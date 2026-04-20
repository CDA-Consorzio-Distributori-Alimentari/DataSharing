    def get_enabled_entities(self, option):
        """
        Returns a list of enabled entities (entità) for the given data sharing option.
        """
        from database.repositories.socio_datasharing_repository import SocioDataSharingRepository
        repo = SocioDataSharingRepository(self.db_utils)
        df = repo.get_relations_dataframe(datasharing_code=option.code, only_enabled=True, only_current_tool=True)
        # Return as list of dicts with code and name for UI
        return [
            {"code": row["TC_Soci_Codice"], "name": row["TC_Soci_Ragione_Sociale"]}
            for _, row in df.iterrows()
        ]
