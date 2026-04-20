# Repository per TA_SOTTOSCRIZIONI_RPT
import datetime
import pandas as pd
from .base_repository import BaseRepository

class SottoscrizioniRptRepository(BaseRepository):
    
    DEFAULT_TABLE_NAME = "TA_SOTTOSCRIZIONI_RPT"
    DEFAULT_TABLE_SCHEMA = "dbo"
    COLUMN_MAPPING = {
        "cod_sottoscrizione": "COD_SOTTOSCRIZIONE",
        "nom_sottoscrizione": "NOM_SOTTOSCRIZIONE",
        "cod_rpt": "COD_RPT",
        "nom_rpt": "NOM_RPT",
        "is_general": "IS_GENERAL",
        "cod_stato": "COD_STATO",
        "cod_tipo": "COD_TIPO",
        "tms_inserimento": "TMS_INSERIMENTO",
    }

    def __init__(self, db_manager):
        self.table_schema = self.DEFAULT_TABLE_SCHEMA
        self.table_name = self.DEFAULT_TABLE_NAME
        self.column_mapping = dict(self.COLUMN_MAPPING)
        super().__init__(db_manager)

    def _map_model(self):
        table = self.db_manager._reflect_table(f"{self.table_schema}.{self.table_name}")
        mapper_registry = self.db_manager._sqlalchemy_registry()
        class TaSottoscrizioniRpt:
            pass
        mapper_registry.map_imperatively(TaSottoscrizioniRpt, table)
        return TaSottoscrizioniRpt

    def get_all(self, filters=None):
        return self.get_all_by_filters(filters or {})

    def get_dataframe(self, cod_sottoscrizione=None, cod_rpt=None, cod_stato=None, cod_tipo=None, is_general=None):
        """
        Restituisce un DataFrame con tutte le sottoscrizioni che soddisfano i filtri passati.
        """
        filters = {}
        if cod_sottoscrizione is not None:
            filters[self.column_mapping["cod_sottoscrizione"]] = cod_sottoscrizione
        if cod_rpt is not None:
            filters[self.column_mapping["cod_rpt"]] = cod_rpt
        if cod_stato is not None:
            filters[self.column_mapping["cod_stato"]] = cod_stato
        if cod_tipo is not None:
            filters[self.column_mapping["cod_tipo"]] = cod_tipo
        if is_general is not None:
            filters[self.column_mapping["is_general"]] = is_general
        try:
            df = super().get_dataframe(filters=filters, order_by=None)
            return df if df is not None else pd.DataFrame([])
        except Exception as exc:
            self.db_manager._log_error(f"Error fetching TA_SOTTOSCRIZIONI_RPT dataframe: {exc}")
            return pd.DataFrame([])

    def leggi_attive(self, cod_tipo=None, is_general=0):
        """
        Restituisce un DataFrame con tutte le sottoscrizioni attive (COD_STATO='A') e is_general come richiesto.
        Puoi filtrare anche per cod_tipo se necessario.
        """
        return self.get_dataframe(cod_stato='A', cod_tipo=cod_tipo, is_general=is_general)

    def aggiorna_report(self, cod_sottoscrizione, cod_rpt, nom_rpt):
        """
        Aggiorna COD_RPT e NOM_RPT per una sottoscrizione specifica.
        """
        filters = {self.column_mapping["cod_sottoscrizione"]: cod_sottoscrizione}
        payload = {
            self.column_mapping["cod_rpt"]: cod_rpt,
            self.column_mapping["nom_rpt"]: nom_rpt
        }
        return self.update_by_filters(filters, payload)
    
    def scegli_per_periodo_o_anno(self, periodo: str, cod_tipo: str = None) -> pd.DataFrame:
            """
            Restituisce la sottoscrizione attiva e generale valida per uno specifico periodo (YYYYMM) o anno (YYYY).
            Se cod_tipo è fornito, filtra anche per tipo.
            Restituisce il record più recente se ce ne sono più.
            """
            is_general = 1
            cod_stato = 'A'
            df = self.get_dataframe(cod_stato=cod_stato, cod_tipo=cod_tipo, is_general=is_general)
            if df is None or df.empty:
                return pd.DataFrame([])
            # Seleziona la sottoscrizione più recente (per TMS_INSERIMENTO) se più di una
            if 'TMS_INSERIMENTO' in df.columns:
                df = df.sort_values('TMS_INSERIMENTO', ascending=False)
            return df.head(1)
