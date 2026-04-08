# Repository per TX_DATASHARING_SOCIO
import datetime

from .base_repository import BaseRepository

class TxDatasharingSocioRepository(BaseRepository):
    DEFAULT_TABLE_NAME = "TX_DATASHARING_SOCIO"
    DEFAULT_TABLE_SCHEMA = "dbo"
    COLUMN_MAPPING = {
        "cod_socio": "COD_SOCIO",
        "cod_datasharing": "COD_DATASHARING",
        "num_periodo": "NUM_PERIODO",
        "tms_invio": "TMS_INVIO",
        "nom_file": "NOM_FILE",
        "cod_stato": "COD_STATO",
        "des_errore": "DES_ERRORE",        
        "tms_update": "TMS_UPDATE",
        "nom_utente_operazione": "NOM_UTENTE_OPERAZIONE",
        "nom_host_operazione": "NOM_HOST_OPERAZIONE",
    }

    def __init__(self, db_manager, tracking_config=None):
        self.tracking_config = tracking_config or {}
        self.table_schema = self.DEFAULT_TABLE_SCHEMA
        self.table_name = self.DEFAULT_TABLE_NAME
        self.column_mapping = dict(self.COLUMN_MAPPING)
        super().__init__(db_manager)

    def _map_model(self):
        tracking_table = self.db_manager._reflect_table(f"{self.table_schema}.{self.table_name}")
        mapper_registry = self.db_manager._sqlalchemy_registry()

        class TxDatasharingSocio:
            pass

        mapper_registry.map_imperatively(TxDatasharingSocio, tracking_table)
        return TxDatasharingSocio

    def _truncate_to_minute(self, dt):
        if dt is None:
            return None
        return dt.replace(second=0, microsecond=0)

    def add_entry(self, values):
        tms_invio = self._truncate_to_minute(values.get("tms_invio"))
        tms_update = self._truncate_to_minute(values.get("tms_update"))
        return self.add({
            self.column_mapping["cod_socio"]: values.get("cod_socio"),
            self.column_mapping["cod_datasharing"]: values.get("cod_datasharing"),
            self.column_mapping["num_periodo"]: values.get("num_periodo"),
            self.column_mapping["tms_invio"]: tms_invio,
            self.column_mapping["nom_file"]: values.get("nom_file"),
            self.column_mapping["cod_stato"]: values.get("cod_stato"),
            self.column_mapping["des_errore"]: values.get("des_errore"),
            self.column_mapping["tms_update"]: tms_update,
            self.column_mapping["nom_utente_operazione"]: values.get("nom_utente_operazione"),
            self.column_mapping["nom_host_operazione"]: values.get("nom_host_operazione"),
        })

    def upsert_entry(self, values):
        tms_invio = self._truncate_to_minute(values.get("tms_invio"))
        tms_update = self._truncate_to_minute(values.get("tms_update"))
        filters = {
            self.column_mapping["cod_socio"]: values.get("cod_socio"),
            self.column_mapping["cod_datasharing"]: values.get("cod_datasharing"),
            self.column_mapping["num_periodo"]: values.get("num_periodo"),
            self.column_mapping["tms_invio"]: tms_invio,
        }
        existing_entry = self.get_first_by_filters(filters)
        payload = {
            self.column_mapping["cod_socio"]: values.get("cod_socio"),
            self.column_mapping["cod_datasharing"]: values.get("cod_datasharing"),
            self.column_mapping["num_periodo"]: values.get("num_periodo"),
            self.column_mapping["tms_invio"]: tms_invio,
            self.column_mapping["nom_file"]: values.get("nom_file"),
            self.column_mapping["cod_stato"]: values.get("cod_stato"),
            self.column_mapping["des_errore"]: values.get("des_errore"),
            self.column_mapping["tms_update"]: tms_update,
            self.column_mapping["nom_utente_operazione"]: values.get("nom_utente_operazione"),
            self.column_mapping["nom_host_operazione"]: values.get("nom_host_operazione"),
        }
        if existing_entry is None:
            return self.add(payload)
        return self.update_by_filters(filters, payload)

    def update_nomefile(self, cod_socio, cod_datasharing, num_periodo, tms_invio, nom_file):
        tms_invio_trunc = self._truncate_to_minute(tms_invio)
        filters = {
            self.column_mapping["cod_socio"]: cod_socio,
            self.column_mapping["cod_datasharing"]: cod_datasharing,
            self.column_mapping["num_periodo"]: num_periodo,
            self.column_mapping["tms_invio"]: tms_invio_trunc,
        }
        payload = {
            self.column_mapping["nom_file"]: nom_file,
            self.column_mapping["tms_update"]: datetime.datetime.now()
        }
        return self.update_by_filters(filters, payload)
    
    def update_status(self, cod_socio, cod_datasharing, num_periodo, tms_invio, cod_stato, des_errore=None):
        tms_invio_trunc = self._truncate_to_minute(tms_invio)
        filters = {
            self.column_mapping["cod_socio"]: cod_socio,
            self.column_mapping["cod_datasharing"]: cod_datasharing,
            self.column_mapping["num_periodo"]: num_periodo,
            self.column_mapping["tms_invio"]: tms_invio_trunc,
        }
        payload = {
            self.column_mapping["cod_stato"]: cod_stato,
            self.column_mapping["tms_update"]: datetime.datetime.now()
        }
        if des_errore is not None:
            payload[self.column_mapping["des_errore"]] = des_errore
        return self.update_by_filters(filters, payload)