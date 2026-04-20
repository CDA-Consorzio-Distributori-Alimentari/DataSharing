# Repository per TD_RPT_SOCIO_PERIODO
import pandas as pd
from datetime import datetime
from .base_repository import BaseRepository

class TdRptSocioPeriodoRepository(BaseRepository):
    DEFAULT_TABLE_NAME = "TD_RPT_SOCIO_PERIODO"
    DEFAULT_TABLE_SCHEMA = "dbo"
    COLUMN_MAPPING = {
        "id_socio": "ID_SOCIO",
        "num_periodo": "NUM_PERIODO",
        "cod_sottoscrizione": "COD_SOTTOSCRIZIONE",
        "cod_obj": "COD_OBJ",
        "cod_esecuzione": "COD_ESECUZIONE",
        "cod_stato": "COD_STATO",
    }

    def __init__(self, db_manager):
        self.table_schema = self.DEFAULT_TABLE_SCHEMA
        self.table_name = self.DEFAULT_TABLE_NAME
        self.column_mapping = dict(self.COLUMN_MAPPING)
        super().__init__(db_manager)

    def _map_model(self):
        table = self.db_manager._reflect_table(f"{self.table_schema}.{self.table_name}")
        mapper_registry = self.db_manager._sqlalchemy_registry()
        class TdRptSocioPeriodo:
            pass
        mapper_registry.map_imperatively(TdRptSocioPeriodo, table)
        return TdRptSocioPeriodo

    def get_all(self, filters=None):
        return self.get_all_by_filters(filters or {})

    def get_dataframe(self, id_socio=None, num_periodo=None, cod_sottoscrizione=None, cod_obj=None, cod_esecuzione=None, cod_stato=None):
        filters = {}
        if id_socio is not None:
            filters[self.column_mapping["id_socio"]] = id_socio
        if num_periodo is not None:
            filters[self.column_mapping["num_periodo"]] = num_periodo
        if cod_sottoscrizione is not None:
            filters[self.column_mapping["cod_sottoscrizione"]] = cod_sottoscrizione
        if cod_obj is not None:
            filters[self.column_mapping["cod_obj"]] = cod_obj
        if cod_esecuzione is not None:
            filters[self.column_mapping["cod_esecuzione"]] = cod_esecuzione
        if cod_stato is not None:
            filters[self.column_mapping["cod_stato"]] = cod_stato
        try:
            df = super().get_dataframe(filters=filters, order_by=None)
            return df if df is not None else pd.DataFrame([])
        except Exception as exc:
            self.db_manager._log_error(f"Error fetching TD_RPT_SOCIO_PERIODO dataframe: {exc}")
            return pd.DataFrame([])

   
        query_narrowcast = f"""
            SELECT 
                TC_Soci_Codice AS ID_SOCIO,
                TW_Narrowcast_Periodo AS NUM_PERIODO,
                TW_Narrowcast_Stato AS COD_STATO,
                TW_Narrowcast_Import AS COD_IMPORT
            FROM TW_Narrowcast
            ORDER BY TC_Soci_Codice
            """
        df_narrowcast = db_utils.execute_select_query_to_dataframe(query_narrowcast)
        if df_narrowcast.empty:
            self.db_manager._log_info("Nessuna riga trovata in TW_Narrowcast.")
            return None
        return df_narrowcast

    
        """
        Restituisce un DataFrame con i flussi filtrati per periodo e logica di stato/attività custom.
        """
        query = f"""
            SELECT
                f.TC_Soci_Codice,
                f.TC_Soci_Polo,
                f.TC_Flussi_Periodo,
                f.TC_Flussi_Tipo_Flussi,
                f.TC_Flussi_Stato_Flusso,
                f.TC_Flussi_Periodo_Riferimento
            FROM TC_Flussi f
            INNER JOIN TC_Soci s ON f.TC_Soci_Codice = s.TC_Soci_Codice
            WHERE 
                f.TC_Flussi_Periodo = {periodo}
                AND s.TC_Soci_Socio_Attivo > 0
                AND (
                    f.TC_Flussi_Stato_Flusso NOT IN (0, -1)                                                
                    OR (f.TC_Flussi_Stato_Flusso = -1 AND f.TC_Flussi_Tipo_Flussi NOT IN (1, 3, 4, 5))                                                
                    OR (f.TC_Flussi_Stato_Flusso = 0 AND f.TC_Flussi_Tipo_Flussi != 2)
                )
        """
        df = db_utils.execute_select_query_to_dataframe(query)
        if df.empty:
            self.db_manager._log_info("Nessuna riga trovata in TcFlussi.")
            return None
        return df

    def leggo_TD_RPT_SOCIO_PERIODO(self):
        """
        Restituisce tutte le righe con cod_esecuzione 'run' o 'ins' come DataFrame.
        """
        df_run = self.get_dataframe(cod_esecuzione="run")
        df_ins = self.get_dataframe(cod_esecuzione="ins")
        if df_run.empty and df_ins.empty:
            self.db_manager._log_info("Nessuna riga trovata in TD_RPT_SOCIO_PERIODO.")
            return None
        df = pd.concat([df_run, df_ins], ignore_index=True)
        return df

    def leggo_esecuzione_TD_RPT_SOCIO_PERIODO(self, codesecuzione: str):
        """
        Restituisce un DataFrame filtrato per COD_ESECUZIONE.
        """
        df = self.get_dataframe(cod_esecuzione=codesecuzione)
        if df.empty:
            self.db_manager._log_info("Nessuna riga trovata in TD_RPT_SOCIO_PERIODO.")
            return None
        return df

    def check_TD_RPT_SOCIO_PERIODO(self, cod_sottoscrizione, cod_rpt, periodo, cod_socio):
        filters = {
            self.column_mapping["id_socio"]: cod_socio,
            self.column_mapping["num_periodo"]: periodo,
            self.column_mapping["cod_sottoscrizione"]: cod_sottoscrizione
        }
        entry = self.get_first_by_filters(filters)
        if entry is not None:
            cod_stato_attuale = getattr(entry, self.column_mapping["cod_stato"])
            if cod_stato_attuale != 'INS':
                self.aggiorna_TD_RPT_SOCIO_PERIODO(
                    id_socio=cod_socio,
                    num_periodo=periodo,
                    cod_sottoscrizione=cod_sottoscrizione,
                    cod_esecuzione='NULL',
                    cod_stato='INS'
                )
                self.db_manager._log_info(f"✅ Aggiornato periodo {periodo} a COD_STATO = 'INS'")
            else:
                self.db_manager._log_info(f"ℹ️ Periodo {periodo} già con COD_STATO = 'INS', nessun aggiornamento necessario.")
        else:
            self.inserisci_TD_RPT_SOCIO_PERIODO(
                id_socio=cod_socio,
                num_periodo=periodo,
                cod_sottoscrizione=cod_sottoscrizione,
                cod_report=cod_rpt,
                cod_stato='INS'
            )
            self.db_manager._log_info(f"✅ Inserita nuova riga per periodo {periodo} con COD_STATO = 'I'")

    def inserisci_TD_RPT_SOCIO_PERIODO(
        self,
        id_socio: int,
        num_periodo: int,
        cod_sottoscrizione: str,
        cod_report: str,
        cod_stato: str,        
        tms_esecuzione: 'datetime' = None,
        des_error: str = None
    ):
        """
        Inserisce una riga in TD_RPT_SOCIO_PERIODO con tutti i campi richiesti.
        """
        if not isinstance(id_socio, int) or not isinstance(num_periodo, int):
            raise ValueError("ID_SOCIO e NUM_PERIODO devono essere interi.")
        if not isinstance(cod_sottoscrizione, str) or not cod_sottoscrizione:
            raise ValueError("cod_sottoscrizione deve essere una stringa non vuota.")   
        if not isinstance(cod_stato, str) or cod_stato not in ("INS", "RUN","OKS", "ERR"):
            raise ValueError("cod_stato deve essere INS, RUN, OKS, ERR")
        if not isinstance(des_error, (str, type(None))):
            raise ValueError("des_error deve essere una stringa o None.")
        if tms_esecuzione is not None and not isinstance(tms_esecuzione, datetime):
            raise ValueError("tms_esecuzione deve essere un datetime o None.")
        payload = {
            self.column_mapping["id_socio"]: id_socio,
            self.column_mapping["num_periodo"]: num_periodo,
            self.column_mapping["cod_sottoscrizione"]: cod_sottoscrizione,
            self.column_mapping["cod_obj"]: cod_report,
            self.column_mapping["cod_esecuzione"]: None,
            self.column_mapping["cod_stato"]: cod_stato,
        }
        if des_error is not None:
            payload["DES_ERROR"] = des_error
        return self.add(payload)

    def aggiorna_TD_RPT_SOCIO_PERIODO(self, id_socio: int, num_periodo: int, cod_sottoscrizione: str, cod_esecuzione: str, cod_stato: str = "A", des_error: str = None):
        """
        Aggiorna una riga in TD_RPT_SOCIO_PERIODO con i parametri forniti.
        """
        filters = {
            self.column_mapping["id_socio"]: id_socio,
            self.column_mapping["num_periodo"]: num_periodo,
            self.column_mapping["cod_sottoscrizione"]: cod_sottoscrizione
        }
        payload = {
            self.column_mapping["cod_esecuzione"]: cod_esecuzione,
            self.column_mapping["cod_stato"]: cod_stato
        }
        if des_error is not None:
            payload["DES_ERROR"] = des_error
        return self.update_by_filters(filters, payload)

