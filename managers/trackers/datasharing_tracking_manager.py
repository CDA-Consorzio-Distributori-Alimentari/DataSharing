from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re


@dataclass
class DataSharingTrackingSession:
    socio: str
    periodo: str
    data_sharing_code: str
    socio_data: object
    log_entries: list[str] = field(default_factory=list)


class DataSharingTrackingManager:
    #DEFAULT_TRACKED_CODES = {"CC001", "CC002"}

    def __init__(self, db_manager, tracking_config=None, log_manager=None, debug_enabled=False):
        self.db_manager = db_manager
        self.tracking_config = tracking_config or {}
        self.log = log_manager
        self.debug_enabled = debug_enabled

    def supports(self, config_ds):
        if not self.tracking_config.get("enabled", True):
            return False

        tracked_codes = {
            str(code).strip()
            for code in self.tracking_config.get("tracked_codes", set())
            if str(code).strip()
        }
        return getattr(config_ds, "code", None) in tracked_codes

    def start_session(self, socio, periodo, config_ds, socio_data):
        session = DataSharingTrackingSession(
            socio=str(socio).strip(),
            periodo=str(periodo).strip(),
            data_sharing_code=getattr(config_ds, "code", ""),
            socio_data=socio_data,
        )
        self.append(session, "** Inizio Elaborazione **")
        self.append(session, self._build_socio_process_log(session.socio, socio_data))
        return session

    def append(self, session, message):
        session.log_entries.append(f"<{message}   {datetime.now().strftime('%H:%M:%S')}>")

    def persist(self, session, output_file=None):
        if self.debug_enabled:
            if self.log is not None:
                self.log.info("Modalita debug attiva: tracking Coca Cola non persistito su database.")
            return

        socio_row = self._get_socio_row(session.socio_data)
        self.db_manager.add_coca_cola_tracking_entry(
            {
                "socio_code": int(socio_row.get("TC_Soci_Codice", session.socio)),
                "socio_polo": socio_row.get("TC_Soci_Polo"),
                "wholesaler_id": socio_row.get("WholesalerID") or socio_row.get("TC_Soci_CocaCola_Codice"),
                "period": int(session.periodo),
                "flow_number": self._resolve_flow_number(output_file) if output_file else 1,
                "log": "  ".join(session.log_entries),
            },
            tracking_config=self.tracking_config,
        )

    def _build_socio_process_log(self, socio, socio_data):
        socio_row = self._get_socio_row(socio_data)
        if not socio_row:
            return f"Socio     {socio}"

        wholesaler_id = str(socio_row.get("WholesalerID", "") or socio_row.get("TC_Soci_CocaCola_Codice", "") or "").strip()
        socio_code = str(socio_row.get("TC_Soci_Codice", socio) or "").strip()
        socio_polo = str(socio_row.get("TC_Soci_Polo", "") or "").strip()
        social_name = str(socio_row.get("TC_Soci_Ragione_Sociale", "") or "").strip()
        return f"Socio     {wholesaler_id} {socio_code} {socio_polo} {social_name}".strip()

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

    @staticmethod
    def _resolve_flow_number(output_file):
        file_name = Path(output_file).stem
        match = re.search(r"_(\d+)$", file_name)
        if match:
            return int(match.group(1))
        return 1
