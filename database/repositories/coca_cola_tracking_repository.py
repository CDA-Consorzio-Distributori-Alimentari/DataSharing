from .base_repository import BaseRepository


class CocaColaTrackingRepository(BaseRepository):
    DEFAULT_TABLE_NAME = "tc_Coca_Cola"
    DEFAULT_TABLE_SCHEMA = "dbo"
    COLUMN_NAMES = {
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
        self.table_schema, self.table_name = self._resolve_table_name(self.tracking_config.get("table"))
        self.column_names = dict(self.COLUMN_NAMES)
        super().__init__(db_manager)

    def _resolve_table_name(self, configured_table_name):
        if not configured_table_name:
            return self.DEFAULT_TABLE_SCHEMA, self.DEFAULT_TABLE_NAME

        schema_name, table_name = self.db_manager._parse_table_name(configured_table_name)
        return schema_name or self.DEFAULT_TABLE_SCHEMA, table_name

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
                self.column_names["socio_code"]: values.get("socio_code"),
                self.column_names["socio_polo"]: values.get("socio_polo"),
                self.column_names["wholesaler_id"]: values.get("wholesaler_id"),
                self.column_names["period"]: values.get("period"),
                self.column_names["flow_number"]: values.get("flow_number"),
                self.column_names["log"]: values.get("log"),
                self.column_names["created_at"]: values.get("created_at"),
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
            self.column_names["socio_code"]: values.get("socio_code"),
            self.column_names["socio_polo"]: values.get("socio_polo"),
            self.column_names["wholesaler_id"]: values.get("wholesaler_id"),
            self.column_names["period"]: values.get("period"),
            self.column_names["flow_number"]: values.get("flow_number"),
        }
        existing_entry = self.get_first_by_filters(filters)
        payload = {
            self.column_names["socio_code"]: values.get("socio_code"),
            self.column_names["socio_polo"]: values.get("socio_polo"),
            self.column_names["wholesaler_id"]: values.get("wholesaler_id"),
            self.column_names["period"]: values.get("period"),
            self.column_names["flow_number"]: values.get("flow_number"),
            self.column_names["log"]: values.get("log"),
            self.column_names["created_at"]: values.get("created_at"),
        }

        if existing_entry is None:
            return self.add(payload)

        payload[self.column_names["log"]] = self._merge_log(
            getattr(existing_entry, self.column_names["log"], None),
            values.get("log"),
        )

        return self.update_by_filters(filters, payload)