from exceptions.blocking_process_error import BlockingProcessError
from exceptions.data_sharing_warning import DataSharingWarning
from services.config import Config
from services.data_sharing_config import DeliveryMethod, FileType, Option
from .log_manager import LogManager
from datetime import datetime
from io import BytesIO

from database import DBManager
from .outputters import FTPManager, MailManager
from .formatters import XMLManager, CSVManager, ExcelManager
from .trackers import DataSharingTrackingManager
import pandas as pd  # Ensure pandas is imported
import os
from pathlib import Path
import re
import traceback
from database.repositories.tabella_logging_repository import TabellaLoggingRepository

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
        self._data_sharing_tracking_manager = None

        # Logger condiviso e accesso al database.
        self.log = LogManager(self.config.log_file, self.config.log_level)
        self.db_manager = DBManager(self.log)

    def _build_result(self, success, message, output_file=None, error_details=None):
        return {
            "success": success,
            "message": message,
            "output_file": output_file,
            "delivery": None,
            "error_details": error_details,
        }

    @staticmethod
    def _is_successful_delivery_result(result):
        delivery = result.get("delivery") or {}
        published = delivery.get("published")
        if published is False:
            return False
        return bool(result.get("success"))

    @staticmethod
    def _get_socio_row(socio_data):
        if socio_data is None:
            return {}
        if hasattr(socio_data, "empty") and socio_data.empty:
            return {}
        if hasattr(socio_data, "iloc"):
            socio_row = socio_data.iloc[0]
            if hasattr(socio_row, "to_dict"):
                return socio_row.to_dict()
            return socio_row
        if hasattr(socio_data, "to_dict"):
            return socio_data.to_dict()
        return socio_data

    def _build_summary_subject(self, config_ds: Option, socio_row):
        socio_name = str(socio_row.get("TC_Soci_Ragione_Sociale", "") or "").strip()
        socio_code = str(socio_row.get("TC_Soci_Codice", "") or "").strip()
        subject_parts = ["DataSharing", config_ds.name]
        if socio_name or socio_code:
            subject_parts.append("-")
            subject_parts.append(" ".join(part for part in [socio_code, socio_name] if part).strip())
        return " ".join(part for part in subject_parts if part).strip()

    def _send_summary_message(self, subject, body, log_context, force_send=False):
        if self.config.debug:
            self.log.info(f"Modalita debug attiva: mail di recap saltata per {log_context}.")
            return

        if not force_send and not self.config.summary_mail_enabled:
            self.log.info(f"Mail di recap disabilitata da configurazione. Invio saltato per {log_context}.")
            return

        try:
            self.log.info(f"Invio mail di recap verso {self.mail_manager.summary_recipient} per {log_context}.")
            self.mail_manager.send_summary_mail(subject, body)
            self.log.info(f"Mail di recap inviata verso {self.mail_manager.summary_recipient} per {log_context}.")
        except Exception as exc:
            self.log.error(f"Invio mail di recap fallito: {exc}")

    @staticmethod
    def _build_delivery_summary(config_ds: Option, result):
        delivery = result.get("delivery") or {}
        recipients = delivery.get("recipients") or []
        files = delivery.get("files") or []
        published = delivery.get("published")

        if published is False:
            recipients = ["Pubblicazione non eseguita"]
        elif not recipients:
            if config_ds.delivery_method == DeliveryMethod.FTP:
                recipients = [f"FTP {getattr(config_ds.config, 'host', '')}".strip()]
            elif config_ds.delivery_method == DeliveryMethod.NASSHARE:
                recipients = [getattr(config_ds.config, "deposit_address", "") or "NAS Share"]
            else:
                recipients = [str(config_ds.delivery_method)]

        if not files and result.get("output_file"):
            files = [os.path.basename(result.get("output_file"))]

        return {
            "published": published,
            "recipients": [str(recipient).strip() for recipient in recipients if str(recipient).strip()],
            "files": [str(file_name).strip() for file_name in files if str(file_name).strip()],
        }

    def _send_summary_mail(self, socio, periodo, config_ds: Option, socio_data, result):
        socio_row = self._get_socio_row(socio_data)
        delivery = self._build_delivery_summary(config_ds, result)
        delivery_ok = self._is_successful_delivery_result(result)
        subject_prefix = "OK" if delivery_ok else "ERRORE"
        subject = f"{subject_prefix} - {self._build_summary_subject(config_ds, socio_row)}"

        socio_code = str(socio_row.get("TC_Soci_Codice", socio) or socio).strip()
        socio_name = str(socio_row.get("TC_Soci_Ragione_Sociale", "") or "").strip()
        recipient_lines = delivery["recipients"] or [""]
        file_lines = delivery["files"] or [os.path.basename(result.get("output_file") or "")]
        delivery_status = "OK" if delivery_ok else "KO"
        error_details = str(result.get("error_details") or "").strip()

        body_lines = [
            f"Esito: {delivery_status}",
            f"Data sharing codice: {config_ds.code}",
            f"Data sharing nome: {config_ds.name}",
            f"Socio codice: {socio_code}",
            f"Socio nome: {socio_name}",
            f"Periodo: {periodo}",
            f"Modalita invio: {config_ds.delivery_method}",
            "Inviato a:",
            *[f"- {recipient}" for recipient in recipient_lines],
            "Elenco file:",
            *[f"- {file_name}" for file_name in file_lines if file_name],
            f"Percorso locale: {result.get('output_file') or ''}",
            f"Messaggio: {result.get('message', '')}",
        ]

        if delivery.get("published") is False:
            body_lines.insert(7, "Pubblicazione: non eseguita")

        if error_details:
            body_lines.extend([
                "Dettaglio errore:",
                error_details,
            ])

        self._send_summary_message(
            subject,
            "\n".join(body_lines),
            f"data sharing {config_ds.code}, socio {socio_code}, periodo {periodo}",
            force_send=not delivery_ok,
        )

    def send_aggregated_summary_mail(self, socio, periods, config_ds: Option, socio_data, aggregated_result, period_results):
        socio_row = self._get_socio_row(socio_data)
        socio_code = str(socio_row.get("TC_Soci_Codice", socio) or socio).strip()
        socio_name = str(socio_row.get("TC_Soci_Ragione_Sociale", "") or "").strip()
        summary_subject = self._build_summary_subject(config_ds, socio_row)
        year_label = str(periods[0])[:4] if periods else ""
        aggregate_ok = all(self._is_successful_delivery_result(item) for item in period_results)
        subject_prefix = "OK" if aggregate_ok else "ERRORE"
        if year_label:
            summary_subject = f"{subject_prefix} - {summary_subject} - riepilogo annuale {year_label}"
        else:
            summary_subject = f"{subject_prefix} - {summary_subject} - riepilogo multi-periodo"

        success_count = sum(1 for item in period_results if self._is_successful_delivery_result(item))
        file_lines = []
        detail_lines = []
        for period_value, period_result in zip(periods, period_results):
            delivery = self._build_delivery_summary(config_ds, period_result)
            delivery_targets = ", ".join(delivery["recipients"]) if delivery["recipients"] else "n.d."
            period_files = delivery["files"] or []
            if not period_files and period_result.get("output_file"):
                period_files = [os.path.basename(period_result.get("output_file"))]
            for file_name in period_files:
                file_lines.append(f"- {period_value}: {file_name}")
            detail_lines.append(
                "- "
                + f"{period_value}: {'OK' if self._is_successful_delivery_result(period_result) else 'KO'}"
                + f" | Invio: {delivery_targets}"
                + (f" | File: {', '.join(period_files)}" if period_files else "")
                + (f" | Messaggio: {period_result.get('message', '')}" if period_result.get("message") else "")
            )

            error_details = str(period_result.get("error_details") or "").strip()
            if error_details:
                detail_lines.append(f"  Dettaglio errore: {error_details}")

        body_lines = [
            f"Esito: {'OK' if aggregate_ok else 'KO'}",
            f"Data sharing codice: {config_ds.code}",
            f"Data sharing nome: {config_ds.name}",
            f"Socio codice: {socio_code}",
            f"Socio nome: {socio_name}",
            f"Anno richiesto: {year_label}",
            f"Periodi richiesti: {', '.join(periods)}",
            f"Periodi elaborati con successo: {success_count}/{len(period_results)}",
            "Elenco file:",
            *(file_lines or ["- Nessun file generato"]),
            "Dettaglio periodi:",
            *detail_lines,
            f"Messaggio finale: {aggregated_result.get('message', '')}",
            f"Percorsi locali: {aggregated_result.get('output_file') or ''}",
        ]

        self._send_summary_message(
            summary_subject,
            "\n".join(body_lines),
            f"data sharing {config_ds.code}, socio {socio_code}, riepilogo annuale {year_label or 'multi-periodo'}",
            force_send=not aggregate_ok,
        )

    def _finalize_result(self, socio, periodo, config_ds: Option, socio_data, result, send_summary_mail=True):
        if send_summary_mail:
            self._send_summary_mail(socio, periodo, config_ds, socio_data, result)
        return result

    def _build_output_directory(self, socio, config_ds: Option):
        output_dir = os.path.join(self.config.output_path, str(socio).strip(), config_ds.code)
        os.makedirs(output_dir, exist_ok=True)
        return output_dir

    def _build_naming_context(self, socio, periodo, config_ds: Option, database_results=None, socio_data=None):
        context = {
            "SOCIO": str(socio).strip(),
            "PERIODO": str(periodo),
            "YYYY_PERIODO": str(periodo)[:4],
            "MM_PERIODO": str(periodo)[4:6],
            "DATASHARING_CODE": config_ds.code,
            "FILE_TYPE": config_ds.file_type,
        }

        socio_row = self._get_socio_row(socio_data)
        relation_wholesaler_id = str(socio_row.get("WholesalerID", "") or "").strip()
        if relation_wholesaler_id:
            context["WholesalerID"] = relation_wholesaler_id

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

    def _resolve_naming_convention(self, socio, config_ds: Option, periodo, database_results=None, socio_data=None):
        current_datetime = datetime.now()
        naming_convention = getattr(config_ds, "naming_convention", None)
        if not naming_convention:
            naming_convention = f"{config_ds.code}_{current_datetime.strftime('%Y%m%d%H%M%S')}"

        for placeholder, fmt in self.config.placeholders.items():
            naming_convention = naming_convention.replace(placeholder, current_datetime.strftime(fmt))

        naming_context = self._build_naming_context(socio, periodo, config_ds, database_results, socio_data)
        return self._replace_named_placeholders(naming_convention, naming_context)

    @staticmethod
    def _resolve_output_extension(file_type):
        normalized_file_type = str(file_type).strip().lower().lstrip(".")
       
        return f".{normalized_file_type}"

    def _build_output_file_path(self, socio, config_ds: Option, periodo, database_results=None, socio_data=None):
        extension = self._resolve_output_extension(config_ds.file_type)
        output_dir = self._build_output_directory(socio, config_ds)

        naming_convention = self._resolve_naming_convention(socio, config_ds, periodo, database_results, socio_data)

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

    def _create_output_artifact(self, socio, periodo, config_ds: Option, database_results, socio_data=None):
        # Costruisce il contenuto una sola volta e restituisce lo stream in
        # memoria; il salvataggio su disco avviene in un punto unico separato.
        output_file = self._build_output_file_path(socio, config_ds, periodo, database_results, socio_data)
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
        if self.config.debug:
            self.log.info(
                f"Modalita debug attiva: pubblicazione saltata per {config_ds.code}. File mantenuto solo in locale: {output_file}."
            )
            return {
                "published": False,
                "recipients": [],
                "files": [os.path.basename(output_file)],
            }

        if config_ds.delivery_method == DeliveryMethod.FTP:
            file_name = os.path.basename(output_file)
            self.log.info(f"Pubblicazione FTP del file {file_name} per data sharing {config_ds.code}.")
            self.get_ftp_manager(config_ds).upload_file(file_name, delivery_stream)
            sent_files = [file_name]
            if getattr(config_ds.config, "create_ok_file", False):
                sent_files.append(f"{Path(file_name).stem}.ok")
            return {
                "published": True,
                "recipients": [f"FTP {getattr(config_ds.config, 'host', '')}".strip()],
                "files": sent_files,
            }

        return {
            "published": False,
            "recipients": [],
            "files": [os.path.basename(output_file)],
        }

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
    def data_sharing_tracking_manager(self):
        if self._data_sharing_tracking_manager is None:
            self._data_sharing_tracking_manager = DataSharingTrackingManager(
                self.db_manager,
                getattr(self.config, "coca_cola_tracking", {}),
                self.log,
                self.config.debug,
            )
        return self._data_sharing_tracking_manager

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

    def process_data(self, socio, periodo, config_ds: Option, send_summary_mail=True):
        from datetime import datetime
        tx_repo = TabellaLoggingRepository(self.db_manager)
        now = datetime.now()
        host = os.getenv("COMPUTERNAME", "")
        user = os.getenv("USERNAME", "")
        try:
            # 1. Inserimento stato INS appena inizia la lavorazione
            tx_repo.add_entry({
                "cod_socio": socio,
                "cod_datasharing": config_ds.code,
                "num_periodo": periodo,
                "tms_invio": now,
                "nom_file": "",  # Il nome file viene aggiornato in seguito quando è disponibile"",
                "cod_stato": "INS",
                "des_errore": None,
                "tms_update": now,
                "nom_utente_operazione": user,
                "nom_host_operazione": host,
            })

            # 2. Verifica socio autorizzato
            try:
                socio_data = self.verify_socio(socio, config_ds.code)
            except Exception as auth_exc:
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato="ERR",
                    des_errore=str(auth_exc)
                )
                self.log.error(f"Errore autorizzazione socio: {auth_exc}")
                raise BlockingProcessError(f"Utente non abilitato o autorizzazione negata: {auth_exc}")

            tracking_session = None
            if self.data_sharing_tracking_manager.supports(config_ds):
                tracking_session = self.data_sharing_tracking_manager.start_session(socio, periodo, config_ds, socio_data)

            # 3. Carico e preparo la query SQL da eseguire.
            query, error_result = self._load_query_text(socio, periodo, config_ds)
            if error_result:
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato="ERR",
                    des_errore=error_result.get("message")
                )
                if tracking_session is not None:
                    self.data_sharing_tracking_manager.append(tracking_session, "ERRORE LETTURA QUERY")
                    self.data_sharing_tracking_manager.persist(tracking_session)
                raise BlockingProcessError(f"Errore caricamento query: {error_result.get('message')}")

            # 4. Eseguo la query e ottengo il dataset da esportare.
            try:
                database_results = self.db_manager.fetch_all(query)
            except Exception as db_exc:
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato="ERR",
                    des_errore=str(db_exc)
                )
                self.log.error(f"Errore esecuzione query: {db_exc}")
                raise BlockingProcessError(f"Errore accesso DB o query: {db_exc}")

            # 5. Aggiorno stato RUN
            tx_repo.update_status(
                cod_socio=socio,
                cod_datasharing=config_ds.code,
                num_periodo=periodo,
                tms_invio=now,
                cod_stato="RUN",
                des_errore=None,
            )

            # 6. Genero il contenuto e preparo lo stream per salvataggio e delivery.
            try:
                output_file, delivery_stream = self._create_output_artifact(socio, periodo, config_ds, database_results, socio_data)
            except Exception as exc:
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato="ERR",
                    des_errore=str(exc)
                )
                self.log.error(f"Errore generazione artefatto: {exc}")
                raise DataSharingWarning(f"Errore generazione artefatto: {exc}")
            tx_repo.update_nomefile(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    nom_file=os.path.basename(output_file)
                )

            # 7. Salvo il file
            try:
                self._save_output_artifact(config_ds, output_file, delivery_stream)
            except Exception as exc:
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato="ERR",
                    des_errore=f"Salvataggio file fallito: {exc}",
                )
                self.log.error(f"Errore salvataggio file: {exc}")
                raise DataSharingWarning(f"Salvataggio file fallito: {exc}")

            # 8. Pubblico il file
            try:
                delivery_details = self._publish_output(config_ds, output_file, delivery_stream)
                stato_finale = "OK " if delivery_details.get("published") else ("DEG" if self.config.debug else "WAR")
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato=stato_finale,
                    des_errore=None
                )
            except Exception as exc:
                tx_repo.update_status(
                    cod_socio=socio,
                    cod_datasharing=config_ds.code,
                    num_periodo=periodo,
                    tms_invio=now,
                    cod_stato="ERR",
                    des_errore=f"Pubblicazione fallita: {exc}"
                    )
                self.log.error(f"Errore pubblicazione file: {exc}")
                raise DataSharingWarning(f"Pubblicazione fallita: {exc}")

            # 9. Chiusura del flusso con log sintetico dell'esito.
            message = f"Processed data for socio {socio} in {config_ds.file_type} mode. File: {output_file}"
            self.log.info(message)
            self.log.info("Elaborazione completata.")
            success_result = self._build_result(True, message, output_file)
            success_result["delivery"] = delivery_details
            return self._finalize_result(socio, periodo, config_ds, socio_data, success_result, send_summary_mail=send_summary_mail)
        except (BlockingProcessError, DataSharingWarning):
            raise
        except Exception as exc:
            # Rilancia l'eccezione per la gestione lato GUI (messagebox)
            raise
        
    def verify_socio(self, socio, datasharing_code=None):
        return self.db_manager.verify_socio(socio, datasharing_code)