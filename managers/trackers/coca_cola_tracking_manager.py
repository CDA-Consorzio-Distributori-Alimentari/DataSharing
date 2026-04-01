from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re


@dataclass
class CocaColaTrackingSession:
    socio: str
    periodo: str
    data_sharing_code: str
    socio_data: object
    log_entries: list[str] = field(default_factory=list)


class CocaColaTrackingManager:
    TRACKED_CODES = {"CC001", "CC002"}

    def __init__(self, db_manager, log_manager=None):
        self.db_manager = db_manager
        self.log = log_manager

    def supports(self, config_ds):
        return getattr(config_ds, "code", None) in self.TRACKED_CODES

    def start_session(self, socio, periodo, config_ds, socio_data):
        session = CocaColaTrackingSession(
            socio=str(socio).strip(),
            periodo=str(periodo).strip(),
            data_sharing_code=getattr(config_ds, "code", ""),
            socio_data=socio_data,
        )
        self.append(session, "** Inizio Elaborazione **")
        self.append(session, self._build_socio_process_log(session.socio, socio_data))
        return session

    def append(self, session, message):
        session.log_entries.append(f"<{message}     {datetime.now().strftime('%H:%M:%S')}>")

    def persist(self, session, output_file=None):
        socio_row = session.socio_data.iloc[0] if session.socio_data is not None and not session.socio_data.empty else {}
        self.db_manager.add_coca_cola_tracking_entry(
            {
                "socio_code": int(socio_row.get("TC_Soci_Codice", session.socio)),
                "socio_polo": socio_row.get("TC_Soci_Polo"),
                "wholesaler_id": socio_row.get("TC_Soci_CocaCola_Codice"),
                "period": int(session.periodo),
                "flow_number": self._resolve_flow_number(output_file) if output_file else 1,
                "log": "  ".join(session.log_entries),
            }
        )

    def _build_socio_process_log(self, socio, socio_data):
        if socio_data is None or (hasattr(socio_data, "empty") and socio_data.empty):
            return f"Socio     {socio}"

        wholesaler_id = str(socio_data.get("TC_Soci_CocaCola_Codice", "") or "").strip()
        socio_code = str(socio_data.get("TC_Soci_Codice", socio) or "").strip()
        social_name = str(socio_data.get("TC_Soci_Ragione_Sociale", "") or "").strip()
        return f"Socio     {wholesaler_id} {socio_code} {social_name}".strip()

    @staticmethod
    def _resolve_flow_number(output_file):
        file_name = Path(output_file).stem
        match = re.search(r"_(\d+)$", file_name)
        if match:
            return int(match.group(1))
        return 1
