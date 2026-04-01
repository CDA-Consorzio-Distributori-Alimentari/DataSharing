import pandas as pd

from .base_repository import BaseRepository


class SocioDataSharingRepository(BaseRepository):
    TABLE_NAME = "TR_Soci_DataSharing"
    TABLE_SCHEMA = "dbo"
    ID_FIELD = "TC_Soci_Codice"

    def _map_model(self):
        sqlalchemy = self.db_manager._require_sqlalchemy()
        mapper_registry = self.db_manager._sqlalchemy_registry()
        metadata = sqlalchemy.MetaData()
        relation_table = sqlalchemy.Table(
            self.TABLE_NAME,
            metadata,
            sqlalchemy.Column("TC_Soci_Codice", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("TC_Soci_Ragione_Sociale", sqlalchemy.String),
            sqlalchemy.Column("DataSharing_Code", sqlalchemy.String, primary_key=True),
            sqlalchemy.Column("DataSharing_Nome", sqlalchemy.String),
            sqlalchemy.Column("WholesalerID", sqlalchemy.String),
            sqlalchemy.Column("Flag_Attivo", sqlalchemy.Boolean),
            sqlalchemy.Column("DataAggiornamento", sqlalchemy.DateTime),
            schema=self.TABLE_SCHEMA,
        )

        class SocioDataSharing:
            pass

        mapper_registry.map_imperatively(SocioDataSharing, relation_table)
        return SocioDataSharing

    def _selectable_columns(self):
        return [getattr(self.model, column_name) for column_name in self.column_names]

    def get_relations_dataframe(self, socio_code=None, datasharing_code=None, only_enabled=False):
        filters = []
        params = []

        if socio_code is not None:
            filters.append("[TC_Soci_Codice] = ?")
            params.append(str(socio_code).strip())

        if datasharing_code is not None:
            filters.append("[DataSharing_Code] = ?")
            params.append(str(datasharing_code).strip())

        if only_enabled:
            filters.append("[Flag_Attivo] = 1")

        where_clause = ""
        if filters:
            where_clause = "WHERE " + " AND ".join(filters)

        selected_columns = ",\n                   ".join(f"[{column_name}]" for column_name in self.column_names)
        query = f"""
            SELECT {selected_columns}
            FROM [cda].[{self.TABLE_SCHEMA}].[{self.TABLE_NAME}]
            {where_clause}
            ORDER BY [TC_Soci_Codice], [DataSharing_Code]
        """

        try:
            sqlalchemy = self.db_manager._require_sqlalchemy()
            query_builder = sqlalchemy.select(*self._selectable_columns())
            if socio_code is not None:
                query_builder = query_builder.where(self.model.TC_Soci_Codice == str(socio_code).strip())
            if datasharing_code is not None:
                query_builder = query_builder.where(self.model.DataSharing_Code == str(datasharing_code).strip())
            if only_enabled:
                query_builder = query_builder.where(self.model.Flag_Attivo == True)
            query_builder = query_builder.order_by(self.model.TC_Soci_Codice, self.model.DataSharing_Code)

            with self.session_factory() as session:
                return pd.DataFrame(session.execute(query_builder).mappings().all())
        except ModuleNotFoundError:
            return self.db_manager.fetch_all(query, tuple(params))
