import pandas as pd

from .base_repository import BaseRepository


class SociRepository(BaseRepository):
    TABLE_NAME = "TC_Soci"
    TABLE_SCHEMA = "dbo"
    ID_FIELD = "TC_Soci_Codice"

    def _map_model(self):
        sqlalchemy = self.db_manager._require_sqlalchemy()
        mapper_registry = self.db_manager._sqlalchemy_registry()
        metadata = sqlalchemy.MetaData()
        soci_table = sqlalchemy.Table(
            self.TABLE_NAME,
            metadata,
            sqlalchemy.Column("TC_Soci_Codice", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("TC_Soci_Polo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Tipo_Clientela_Codice", sqlalchemy.String),
            sqlalchemy.Column("TC_Soci_CocaCola_Attivo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_CocaCola_Codice", sqlalchemy.String),
            sqlalchemy.Column("TC_Soci_CocaCola_In_Chiaro", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_Ragione_Sociale", sqlalchemy.String),
            sqlalchemy.Column("TC_Soci_Campari_Attivo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_Socio_Attivo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_Ferrero_Attivo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_DIAGEO_Attivo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_RedBull_Attivo", sqlalchemy.Integer),
            sqlalchemy.Column("TC_Soci_Martini_Attivo", sqlalchemy.Integer),
            schema=self.TABLE_SCHEMA,
        )

        class Socio:
            pass

        mapper_registry.map_imperatively(Socio, soci_table)
        return Socio

    def _selectable_columns(self):
        return [getattr(self.model, column_name) for column_name in self.column_names]

    def _build_fallback_query(self):
        selected_columns = ",\n                   ".join(f"[{column_name}]" for column_name in self.column_names)
        return f"""
            SELECT {selected_columns}
            FROM [cda].[{self.TABLE_SCHEMA}].[{self.TABLE_NAME}]
            WHERE [TC_Soci_Socio_Attivo] = 1 AND [TC_Soci_Codice] = ?
            """

    def get_active_socio_dataframe(self, socio_code):
        try:
            sqlalchemy = self.db_manager._require_sqlalchemy()
            query = (
                sqlalchemy.select(*self._selectable_columns())
                .where(self.model.TC_Soci_Socio_Attivo == 1)
                .where(self.model.TC_Soci_Codice == socio_code)
            )

            with self.session_factory() as session:
                result = pd.DataFrame(session.execute(query).mappings().all())
        except ModuleNotFoundError:
            result = self.db_manager.fetch_all(self._build_fallback_query(), (socio_code,))

        if result.empty or result.shape[1] != len(self.column_names):
            self.db_manager._log_warning(f"Unexpected query result for socio {socio_code}.")
            return pd.DataFrame()

        return result
