from .base_repository import BaseRepository


class CocaColaTrackingRepository(BaseRepository):
    DEFAULT_TABLE_NAME = "tc_Coca_Cola"
    DEFAULT_TABLE_SCHEMA = "dbo"
    COLUMN_MAPPING = {
        "socio_code": "tc_soci_codice",
        "socio_polo": "tc_soci_Polo",
        "wholesaler_id": "TC_Soci_CocaCola_Codice",
        "period": "tc_coca_cola_periodo",
        "flow_number": "tc_coca_cola_numero_flusso",
        "log": "tc_coca_cola_log",
        "created_at": "tc_coca_cola_data_creazione",
    }

    def __init__(self, db_manager, tracking_config=None):
        self.tracking_config = tracking_config or {}
        self.table_schema, self.table_name = self._resolve_table_name(db_manager, self.tracking_config.get("table"))
        self.column_mapping = dict(self.COLUMN_MAPPING)
        super().__init__(db_manager)

    @staticmethod
    def _resolve_table_name(db_manager, configured_table_name):
        if not configured_table_name:
            return CocaColaTrackingRepository.DEFAULT_TABLE_SCHEMA, CocaColaTrackingRepository.DEFAULT_TABLE_NAME

        schema_name, table_name = db_manager._parse_table_name(configured_table_name)
        return schema_name or CocaColaTrackingRepository.DEFAULT_TABLE_SCHEMA, table_name

    def _map_model(self):
        tracking_table = self.db_manager._reflect_table(f"{self.table_schema}.{self.table_name}")
        mapper_registry = self.db_manager._sqlalchemy_registry()

        class CocaColaTracking:
            pass

        mapper_registry.map_imperatively(CocaColaTracking, tracking_table)
        return CocaColaTracking

    def add_entry(self, values):
        return self.add(
            {
                self.column_mapping["socio_code"]: values.get("socio_code"),
                self.column_mapping["socio_polo"]: values.get("socio_polo"),
                self.column_mapping["wholesaler_id"]: values.get("wholesaler_id"),
                self.column_mapping["period"]: values.get("period"),
                self.column_mapping["flow_number"]: values.get("flow_number"),
                self.column_mapping["log"]: values.get("log"),
                self.column_mapping["created_at"]: values.get("created_at"),
            }
        )

    @staticmethod
    def _merge_log(existing_log, new_log):
        existing_text = str(existing_log or "").strip()
        new_text = str(new_log or "").strip()
        if existing_text and new_text:
            return f"{existing_text}  {new_text}"
        return existing_text or new_text

    def upsert_entry(self, values):
        filters = {
            self.column_mapping["socio_code"]: values.get("socio_code"),
            self.column_mapping["socio_polo"]: values.get("socio_polo"),
            self.column_mapping["wholesaler_id"]: values.get("wholesaler_id"),
            self.column_mapping["period"]: values.get("period"),
            self.column_mapping["flow_number"]: values.get("flow_number"),
        }
        existing_entry = self.get_first_by_filters(filters)
        payload = {
            self.column_mapping["socio_code"]: values.get("socio_code"),
            self.column_mapping["socio_polo"]: values.get("socio_polo"),
            self.column_mapping["wholesaler_id"]: values.get("wholesaler_id"),
            self.column_mapping["period"]: values.get("period"),
            self.column_mapping["flow_number"]: values.get("flow_number"),
            self.column_mapping["log"]: values.get("log"),
            self.column_mapping["created_at"]: values.get("created_at"),
        }

        if existing_entry is None:
            return self.add(payload)

        payload[self.column_mapping["log"]] = self._merge_log(
            getattr(existing_entry, self.column_mapping["log"], None),
            values.get("log"),
        )

        return self.update_by_filters(filters, payload)