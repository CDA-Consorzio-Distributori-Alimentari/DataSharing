from .base_repository import BaseRepository


class CocaColaTrackingRepository(BaseRepository):
    TABLE_NAME = "tc_Coca_Cola"
    TABLE_SCHEMA = "dbo"
    COLUMN_NAMES = {
        "socio_code": "tc_soci_codice",
        "socio_polo": "tc_soci_Polo",
        "wholesaler_id": "TC_Soci_CocaCola_Codice",
        "period": "tc_coca_cola_periodo",
        "flow_number": "tc_coca_cola_numero_flusso",
        "log": "tc_coca_cola_log",
        "created_at": "tc_coca_cola_data_creazione",
    }

    def __init__(self, db_manager):
        self.column_names = dict(self.COLUMN_NAMES)
        super().__init__(db_manager)

    def _map_model(self):
        tracking_table = self.db_manager._reflect_table(f"{self.TABLE_SCHEMA}.{self.TABLE_NAME}")
        mapper_registry = self.db_manager._sqlalchemy_registry()

        class CocaColaTracking:
            pass

        mapper_registry.map_imperatively(CocaColaTracking, tracking_table)
        return CocaColaTracking

    def add_entry(self, values):
        return self.add(
            {
                self.column_names["socio_code"]: values.get("socio_code"),
                self.column_names["socio_polo"]: values.get("socio_polo"),
                self.column_names["wholesaler_id"]: values.get("wholesaler_id"),
                self.column_names["period"]: values.get("period"),
                self.column_names["flow_number"]: values.get("flow_number"),
                self.column_names["log"]: values.get("log"),
                self.column_names["created_at"]: values.get("created_at"),
            }
        )