from services.config import Config
from services.data_sharing_config import DeliveryMethod, FileType, Option
from .log_manager import LogManager
from datetime import datetime
from io import BytesIO

from database import DBManager
from .outputters import FTPManager, MailManager
from .formatters import XMLManager, CSVManager, ExcelManager
from .trackers import CocaColaTrackingManager
import pandas as pd  # Ensure pandas is imported
import os
from pathlib import Path
import re

class DataSharingOwnerManager:
    def __init__(self):
        self.config = Config()

        # I manager pesanti vengono creati solo quando servono.
        self._ftp_managers = {}
        self._mail_manager = None
        self._xml_manager = None
        self._csv_manager = None
        self._excel_manager = None
        self._coca_cola_tracking_manager = None

        # Logger condiviso e accesso al database.
        self.log = LogManager(self.config.log_file, self.config.log_level)
        self.db_manager = DBManager(self.log)

    def _build_result(self, success, message, output_file=None):
        return {
            "success": success,
            "message": message,
            "output_file": output_file,
        }

    def _build_output_directory(self, socio, config_ds: Option):
        output_dir = os.path.join(self.config.output_path, str(socio).strip(), config_ds.code)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _build_naming_context(self, socio, periodo, config_ds: Option, database_results=None):
        context = {
            "SOCIO": str(socio).strip(),
            "PERIODO": str(periodo),
            "YYYY_PERIODO": str(periodo)[:4],
            "MM_PERIODO": str(periodo)[4:6],
            "DATASHARING_CODE": config_ds.code,
            "FILE_TYPE": config_ds.file_type,
        }

        for key, value in getattr(config_ds, "naming_variables", {}).items():
            context[str(key)] = "" if value is None else str(value).strip()

        if database_results is not None and not database_results.empty:
            first_row = database_results.iloc[0]
            for column_name in database_results.columns:
                value = first_row.get(column_name)
                if pd.isna(value):
                    context[column_name] = ""
                else:
                    context[column_name] = str(value).strip()

        return context

    @staticmethod
    def _replace_named_placeholders(template, context):
        def replace_match(match):
            key = match.group(1)
            return context.get(key, match.group(0))

        return re.sub(r"\{([^{}]+)\}", replace_match, template)

    def _resolve_naming_convention(self, socio, config_ds: Option, periodo, database_results=None):
        current_datetime = datetime.now()
        naming_convention = getattr(config_ds, "naming_convention", None)
        if not naming_convention:
            naming_convention = f"{config_ds.code}_{current_datetime.strftime('%Y%m%d%H%M%S')}"

        for placeholder, fmt in self.config.placeholders.items():
            naming_convention = naming_convention.replace(placeholder, current_datetime.strftime(fmt))

        naming_context = self._build_naming_context(socio, periodo, config_ds, database_results)
        return self._replace_named_placeholders(naming_convention, naming_context)

    def _build_output_file_path(self, socio, config_ds: Option, periodo, database_results=None):
        extension_map = {
            FileType.CSV: ".csv",
            FileType.EXCEL: ".xlsx",
        }
        extension = extension_map.get(config_ds.file_type, f".{config_ds.file_type}")
        output_dir = self._build_output_directory(socio, config_ds)

        naming_convention = self._resolve_naming_convention(socio, config_ds, periodo, database_results)

        if not naming_convention.lower().endswith(extension):
            naming_convention = f"{naming_convention}{extension}"

        return os.path.join(output_dir, naming_convention)

    def _load_query_text(self, socio, periodo, config_ds: Option):
        # Risolve il file SQL configurato e applica i due placeholder runtime
        # usati oggi dal tracciato standard.
        query_file = getattr(config_ds, "query_file", None)
        if not query_file:
            query_file = f"{config_ds.name.lower().replace(' ', '_')}_query.sql"

        query_file = self._resolve_query_file_path(config_ds, query_file)
        self.log.info(f"Caricamento query per data sharing {config_ds.code} da {query_file}.")

        try:
            with open(query_file, "r") as file:
                query = file.read()
        except FileNotFoundError:
            message = f"Query file not found: {query_file}"
            self.log.error(message)
            return None, self._build_result(False, message)

        query = query.replace("@socioelaborazione", f"'{socio}'", 1)
        query = query.replace("@periodoelaborazione", f"'{periodo}'", 1)
        return query, None

    def _create_output_artifact(self, socio, periodo, config_ds: Option, database_results):
        # Costruisce il contenuto una sola volta e restituisce lo stream in
        # memoria; il salvataggio su disco avviene in un punto unico separato.
        output_file = self._build_output_file_path(socio, config_ds, periodo, database_results)
        self.log.info(f"Generazione artefatto {config_ds.file_type} in {output_file}.")

        if config_ds.file_type == FileType.XML:
            xml_content = self.xml_manager.build_xml_content(database_results, config_ds, periodo)
            return output_file, BytesIO(xml_content.encode('utf-8'))

        if config_ds.file_type == FileType.CSV:
            csv_rows = [database_results.columns.tolist(), *database_results.values.tolist()]
            csv_content = self.csv_manager.build_csv_content(csv_rows)
            return output_file, BytesIO(csv_content.encode('utf-8'))

        if config_ds.file_type == FileType.EXCEL:
            excel_rows = [database_results.columns.tolist(), *database_results.values.tolist()]
            excel_content = self.excel_manager.build_excel_content('Sheet1', excel_rows)
            return output_file, BytesIO(excel_content)

        raise ValueError("Unsupported data sharing type")

    def _save_output_artifact(self, config_ds: Option, output_file, delivery_stream):
        # Persisto il contenuto su file una volta sola, riusando lo stesso stream
        # poi anche per la pubblicazione.
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        if hasattr(delivery_stream, 'seek'):
            delivery_stream.seek(0)

        with open(output_file, 'wb') as file:
            file.write(delivery_stream.read())

        if hasattr(delivery_stream, 'seek'):
            delivery_stream.seek(0)

        if config_ds.file_type == FileType.XML:
            self.xml_manager.last_output_file = output_file

        self.log.info(f"Artefatto salvato su disco in {output_file}.")

    def _publish_output(self, config_ds: Option, output_file, delivery_stream):
        # La pubblicazione usa il delivery_method configurato sull'opzione.
        if config_ds.delivery_method == DeliveryMethod.FTP:
            file_name = os.path.basename(output_file)
            self.log.info(f"Pubblicazione FTP del file {file_name} per data sharing {config_ds.code}.")
            self.get_ftp_manager(config_ds).upload_file(file_name, delivery_stream)

    def _resolve_query_file_path(self, config_ds: Option, query_file: str):
        if os.path.isabs(query_file):
            return query_file

        query_root = Path(self.config.querysql_path)
        configured_query_path = Path(query_file)

        candidate_paths = []
        if configured_query_path.parent != Path("."):
            candidate_paths.append((query_root / configured_query_path).resolve(strict=False))
        else:
            candidate_paths.append((query_root / config_ds.code / configured_query_path.name).resolve(strict=False))
            candidate_paths.append((query_root / configured_query_path.name).resolve(strict=False))

        for candidate_path in candidate_paths:
            if candidate_path.exists():
                return str(candidate_path)

        return str(candidate_paths[0])

    def get_ftp_manager(self, config_ds: Option):
        ftp_key = getattr(config_ds, "code", None) or id(config_ds)
        if ftp_key not in self._ftp_managers:
            self._ftp_managers[ftp_key] = FTPManager(option=config_ds, log_manager=self.log)
        return self._ftp_managers[ftp_key]

    @property
    def coca_cola_tracking_manager(self):
        if self._coca_cola_tracking_manager is None:
            self._coca_cola_tracking_manager = CocaColaTrackingManager(
                self.db_manager,
                getattr(self.config, "coca_cola_tracking", {}),
                self.log,
            )
        return self._coca_cola_tracking_manager

    @property
    def mail_manager(self):
        if self._mail_manager is None:
            mail_config = self.config.mail_config
            self._mail_manager = MailManager(**mail_config)
        return self._mail_manager

    @property
    def xml_manager(self):
        if self._xml_manager is None:
            self._xml_manager = XMLManager(self.config)
        return self._xml_manager

    @property
    def csv_manager(self):
        if self._csv_manager is None:
            self._csv_manager = CSVManager()
        return self._csv_manager

    @property
    def excel_manager(self):
        if self._excel_manager is None:
            self._excel_manager = ExcelManager()
        return self._excel_manager

    # def process_data(self, owner, mode, query, output_file):
        # # Fetch data from the database
        # data = self.db_manager.fetch_all(query)

        # # Generate the file based on the mode
        # if mode == 'xml':
        #     xml_content = self.xml_manager.create_xml('Root', {f'Row{i}': str(row) for i, row in enumerate(data)})
        #     self.xml_manager.save_xml(output_file, xml_content)
        # elif mode == 'csv':
        #     self.csv_manager.write_csv(output_file, data)
        # elif mode == 'excel':
        #     self.excel_manager.create_workbook(output_file)
        #     self.excel_manager.write_to_sheet(output_file, 'Sheet1', data)
        # else:
        #     self.log("Unsupported mode")
        #     return

        # # Send the file via FTP
        # self.ftp_manager.upload_file(output_file, f"/remote/path/{output_file}")

        # # Send the file via email
        # subject = f"Data Sharing for {owner}"
        # body = f"Please find attached the data file for {owner}."
        # self.mail_manager.send_mail("recipient@example.com", subject, body)

        # # Log the operation
        # self.log(f"Processed data for {owner} in {mode} mode and sent via FTP and email.")

    def process_data(self, socio, periodo, config_ds :Option): 
        # Il risultato ritorna sempre in forma strutturata, così il metodo
        # può essere riusato sia da CLI sia da una futura API.
        self.log.info(f"Avvio elaborazione per socio {socio}, periodo {periodo}, data sharing {config_ds.code}.")
        tracking_session = None
        if self.coca_cola_tracking_manager.supports(config_ds):
            socio_data = self.verify_socio(socio)
            tracking_session = self.coca_cola_tracking_manager.start_session(socio, periodo, config_ds, socio_data)

        # 1. Carico e preparo la query SQL da eseguire.
        query, error_result = self._load_query_text(socio, periodo, config_ds)
        if error_result:
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "ERRORE LETTURA QUERY")
                self.coca_cola_tracking_manager.persist(tracking_session)
            return error_result

        # 2. Eseguo la query e ottengo il dataset da esportare.
        database_results = self.db_manager.fetch_all(query)

        # Log tecnico per diagnosticare dimensione e forma del risultato.
        self.log.info(f"Raw database results fetched for socio {socio}: {database_results.shape}")

        # 3. Genero il contenuto e preparo lo stream per salvataggio e delivery.
        try:
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "Scrittura file XML")
            output_file, delivery_stream = self._create_output_artifact(socio, periodo, config_ds, database_results)
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "SCRITTURA FILE XML OK")
        except FileNotFoundError as exc:
            message = str(exc)
            self.log.error(message)
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "SCRITTURA FILE XML KO")
                self.coca_cola_tracking_manager.persist(tracking_session)
            return self._build_result(False, message)
        except ValueError as exc:
            message = str(exc)
            self.log.error(message)
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "SCRITTURA FILE XML KO")
                self.coca_cola_tracking_manager.persist(tracking_session)
            return self._build_result(False, message)

        # 4. Salvo il file in un punto unico, indipendente dal tipo output.
        try:
            self._save_output_artifact(config_ds, output_file, delivery_stream)
        except Exception as exc:
            message = f"Creazione stream completata ma salvataggio file fallito: {exc}"
            self.log.error(message)
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "SCRITTURA FILE XML KO")
                self.coca_cola_tracking_manager.persist(tracking_session, output_file)
            return self._build_result(False, message)

        # 5. Pubblico il file sul canale di consegna configurato.
        try:
            if tracking_session is not None and config_ds.delivery_method == DeliveryMethod.FTP:
                self.coca_cola_tracking_manager.append(tracking_session, "INVIO FILE XML...")
            self._publish_output(config_ds, output_file, delivery_stream)
            if tracking_session is not None and config_ds.delivery_method == DeliveryMethod.FTP:
                self.coca_cola_tracking_manager.append(tracking_session, "INVIO FILE XML OK")
        except Exception as exc:
            message = f"File generato ma pubblicazione fallita: {exc}"
            self.log.error(message)
            if tracking_session is not None:
                self.coca_cola_tracking_manager.append(tracking_session, "INVIO FILE XML KO")
                self.coca_cola_tracking_manager.persist(tracking_session, output_file)
            return self._build_result(False, message, output_file)

        if tracking_session is not None:
            self.coca_cola_tracking_manager.persist(tracking_session, output_file)

        # Chiusura del flusso con log sintetico dell'esito.
        message = f"Processed data for socio {socio} in {config_ds.file_type} mode. File: {output_file}"
        self.log.info(message)

        self.log.info("Elaborazione completata.")

        return self._build_result(True, message, output_file)
        
    def verify_socio(self, socio):
        return self.db_manager.verify_socio(socio)