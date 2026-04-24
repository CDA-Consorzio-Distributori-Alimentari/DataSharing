# Repository per TX_DATASHARING_SOCIO
import datetime
import pandas as pd
from .base_repository import BaseRepository

class TabellaLoggingRepository(BaseRepository):
    DEFAULT_TABLE_NAME = "TX_DATASHARING_SOCIO"
    DEFAULT_TABLE_SCHEMA = "dbo"
    COLUMN_MAPPING = {
        "cod_socio": "COD_SOCIO",
        "socio_ragione_sociale": "TC_Soci_Ragione_Sociale",
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
    
    def __init__(self, db_manager):
    
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
            self.column_mapping["socio_ragione_sociale"]: values.get("socio_ragione_sociale"),
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
            self.column_mapping["socio_ragione_sociale"]: values.get("socio_ragione_sociale"),
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

    def get_cod_stato(self, cod_socio, cod_datasharing, num_periodo, tms_invio=None):
        """
        Restituisce il valore di cod_stato dell'ultimo tentativo (tms_invio massimo) per la combinazione fornita.
        Se tms_invio è fornito, filtra anche per tms_invio troncato al minuto.
        """
        filters = {
            self.column_mapping["cod_socio"]: cod_socio,
            self.column_mapping["cod_datasharing"]: cod_datasharing,
            self.column_mapping["num_periodo"]: num_periodo,
        }
        if tms_invio is not None:
            filters[self.column_mapping["tms_invio"]] = self._truncate_to_minute(tms_invio)
        entries = self.get_all_by_filters(filters)
        if not entries:
            return None
        # Ordina per tms_invio discendente e restituisce il cod_stato della più recente
        latest = max(entries, key=lambda e: getattr(e, self.column_mapping["tms_invio"]))
        return getattr(latest, self.column_mapping["cod_stato"], None)
    
    def get_dataframe(self, cod_socio=None, cod_datasharing=None, num_periodo=None, cod_stato=None, tms_invio=None):
        """
        Restituisce un DataFrame pandas filtrato per i parametri forniti.
        Se tms_invio è None, limita ai record degli ultimi 3 anni (incluso l'anno corrente) a livello DB.
        """
        
        filters = {}
        if cod_socio is not None:
            filters[self.column_mapping["cod_socio"]] = cod_socio
        if cod_datasharing is not None:
            filters[self.column_mapping["cod_datasharing"]] = cod_datasharing
        if num_periodo is not None:
            filters[self.column_mapping["num_periodo"]] = num_periodo
        if cod_stato is not None:
            filters[self.column_mapping["cod_stato"]] = cod_stato

      
        try:
            df = super().get_dataframe(filters=filters, order_by=None)
            return df if df is not None else pd.DataFrame([])
        except Exception as exc:
            self.db_manager._log_error(f"Error fetching by dataframe: {exc}")
            return pd.DataFrame([])
    