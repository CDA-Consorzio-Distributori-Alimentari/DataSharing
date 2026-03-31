from services.config import Config
from services.data_sharing_config import Option
from .log_manager import LogManager
from datetime import datetime

from database import DBManager
from .output_manager import OutputManager
from .ftp_manager import FTPManager
from .mail_manager import MailManager
from .xml_manager import XMLManager
from .csv_manager import CSVManager
from .excel_manager import ExcelManager
import json
import pandas as pd  # Ensure pandas is imported
import os

class DataSharingOwnerManager:
    def __init__(self):
        self.config = Config()

                # I manager pesanti vengono creati solo quando servono.
        self._ftp_manager = None
        self._mail_manager = None
        self._xml_manager = None
        self._csv_manager = None
        self._excel_manager = None

                # Logger condiviso e accesso al database.
        self.log = LogManager(self.config.log_file, self.config.log_level)
        self.db_manager = DBManager(self.log)

    def get_auto_execution_config(self):
        return getattr(self.config, "auto_execution", {}) or {}

    def claim_next_auto_job(self):
        auto_config = self.get_auto_execution_config()
        if not auto_config:
            raise ValueError("Configurazione auto_execution mancante in config.json")
        return self.db_manager.claim_next_auto_job(auto_config)

    def complete_auto_job(self, job, success, output_file=None, message=None):
        auto_config = self.get_auto_execution_config()
        if not auto_config:
            raise ValueError("Configurazione auto_execution mancante in config.json")
        ok_status = auto_config.get("status_ok", "OK")
        ko_status = auto_config.get("status_ko", "KO")
        self.db_manager.complete_auto_job(
            auto_config,
            job,
            ok_status if success else ko_status,
            output_file=output_file,
            message=message,
        )

    def _build_result(self, success, message, output_file=None):
        return {
            "success": success,
            "message": message,
            "output_file": output_file,
        }

    def _build_output_file_path(self, config_ds: Option):
        extension_map = {
            "csv": ".csv",
            "excel": ".xlsx",
        }
        extension = extension_map.get(config_ds.file_type, f".{config_ds.file_type}")
        output_dir = os.path.join(self.config.output_path, config_ds.file_type)
        os.makedirs(output_dir, exist_ok=True)

        current_datetime = datetime.now()
        naming_convention = getattr(config_ds, "naming_convention", None)
        if not naming_convention:
            naming_convention = f"{config_ds.code}_{current_datetime.strftime('%Y%m%d%H%M%S')}"

        for placeholder, fmt in self.config.placeholders.items():
            naming_convention = naming_convention.replace(placeholder, current_datetime.strftime(fmt))

        if not naming_convention.lower().endswith(extension):
            naming_convention = f"{naming_convention}{extension}"

        return os.path.join(output_dir, naming_convention)

    @property
    def ftp_manager(self):
        if self._ftp_manager is None:
            ftp_config = self.config.ftp_config
            self._ftp_manager = FTPManager(**ftp_config)
        return self._ftp_manager

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
     

        # Determine the SQL file from configuration, with a legacy fallback.
        query_file = getattr(config_ds, "query_file", None)
        if not query_file:
            # Se la configurazione non specifica il file SQL, uso la convenzione
            # basata sul nome dell'export.
            query_file = f"{config_ds.name.lower().replace(' ', '_')}_query.sql"
        if not os.path.isabs(query_file):
            query_file = os.path.abspath(os.path.join(self.config.querysql_path, query_file))
        

        # Read SQL query from file
        try:
            with open(query_file, "r") as file:
                query = file.read()
        except FileNotFoundError:
            # Se il file SQL manca, interrompo subito e restituisco il motivo.
            message = f"Query file not found: {query_file}"
            self.log.error(message)
            return self._build_result(False, message)

        # Sostituzione minimale dei parametri previsti dalla query.
        query = query.replace("@socioelaborazione", f"'{socio}'", 1)
        query = query.replace("@periodoelaborazione", f"'{periodo}'", 1)


        # Eseguo la query e ottengo il dataset da esportare.
        database_results = self.db_manager.fetch_all(query)
        output_file = None

        # Log tecnico per diagnosticare dimensione e forma del risultato.
        self.log.info(f"Raw database results fetched for socio {socio}: {database_results.shape}")

        # Dispatch sull'export richiesto: XML, CSV o Excel.
        if config_ds.file_type == 'xml':
            try:
                self.xml_manager.create_xml(database_results, config_ds, periodo)
                output_file = self.xml_manager.last_output_file
            except FileNotFoundError as exc:
                message = str(exc)
                self.log.error(message)
                return self._build_result(False, message)
        elif config_ds.file_type == 'csv':
            output_file = self._build_output_file_path(config_ds)
            csv_rows = [database_results.columns.tolist(), *database_results.values.tolist()]
            self.csv_manager.write_csv(output_file, csv_rows)
        elif config_ds.file_type == 'excel':
            output_file = self._build_output_file_path(config_ds)
            excel_rows = [database_results.columns.tolist(), *database_results.values.tolist()]
            self.excel_manager.create_workbook(output_file)
            self.excel_manager.write_to_sheet(output_file, 'Sheet1', excel_rows)
        else:
            message = "Unsupported data sharing type"
            self.log.error(message)
            return self._build_result(False, message)

        # Chiusura del flusso con log sintetico dell'esito.
        message = f"Processed data for socio {socio} in {config_ds.file_type} mode. File: {output_file}"
        self.log.info(message)

        self.log.info("Elaborazione completata.")

        return self._build_result(True, message, output_file)
        
    def verify_socio(self, socio):
        return self.db_manager.verify_socio(socio)