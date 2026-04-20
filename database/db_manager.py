import importlib
from datetime import datetime
import getpass
import os

import pandas as pd
import pyodbc



from services.config import Config
from .repositories import SocioDataSharingRepository, SociRepository, TabellaLoggingRepository


class DBManager:

        
    def __init__(self, log_manager=None):
        config = Config()
        self.connection_string = config.get_connection_string()
        self.log_manager = log_manager
        self._sqlalchemy_engine = None
        self._sqlalchemy_modules = None
        self._sqlalchemy_session_factory = None
        self._soci_repository = None
        self._socio_datasharing_repository = None
        self._coca_cola_tracking_repository = None
        self._tabella_logging_windows = None

    @staticmethod
    def _get_logged_user_for_session_context():
        domain_name = str(os.environ.get("USERDOMAIN", "")).strip()
        username = str(os.environ.get("USERNAME", "")).strip() or getpass.getuser()
        if domain_name and username and username.upper() != "SYSTEM":
            return f"{domain_name}\\{username}"
        return username

    def _apply_session_context(self, connection):
        session_user = self._get_logged_user_for_session_context()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "EXEC sys.sp_set_session_context @key=N'NOM_USER', @value=?",
                    [session_user],
                )
            finally:
                cursor.close()
        except Exception as exc:
            self._log_warning(
                f"Impossibile valorizzare SESSION_CONTEXT(N'NOM_USER') con l'utente {session_user}: {exc}"
            )

    def _open_pyodbc_connection(self):
        connection = pyodbc.connect(self.connection_string)
        self._apply_session_context(connection)
        return connection

    def _log_warning(self, message):
        if self.log_manager is not None:
            self.log_manager.warning(message)

    def _log_error(self, message):
        if self.log_manager is not None:
            self.log_manager.error(message)

    def execute_query(self, query, params=None):
        with self._open_pyodbc_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()
            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)

    def _fetch_all_with_pyodbc(self, query, params=None):
        with self._open_pyodbc_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)

    def fetch_all(self, query, params=None):
        try:
            with self._get_sqlalchemy_engine().connect() as connection:
                result = connection.exec_driver_sql(query, params or ())
                return pd.DataFrame(result.fetchall(), columns=result.keys())
        except ModuleNotFoundError:
            return self._fetch_all_with_pyodbc(query, params)

    def fetch_one(self, query, params=None):
        with self._open_pyodbc_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            return cursor.fetchone()

    def execute_non_query(self, query, params=None):
        with self._open_pyodbc_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()

    def _load_sqlalchemy_modules(self):
        if self._sqlalchemy_modules is None:
            try:
                sqlalchemy = importlib.import_module("sqlalchemy")
                sqlalchemy_engine = importlib.import_module("sqlalchemy.engine")
                sqlalchemy_orm = importlib.import_module("sqlalchemy.orm")
            except ImportError as exc:
                raise ModuleNotFoundError(
                    "SQLAlchemy non installato. Installa il pacchetto 'SQLAlchemy' per usare il layer ORM del database."
                ) from exc

            self._sqlalchemy_modules = {
                "sqlalchemy": sqlalchemy,
                "engine": sqlalchemy_engine,
                "orm": sqlalchemy_orm,
            }
        return self._sqlalchemy_modules

    def _require_sqlalchemy(self):
        return self._load_sqlalchemy_modules()["sqlalchemy"]

    def _sqlalchemy_registry(self):
        return self._load_sqlalchemy_modules()["orm"].registry()

    def _get_sqlalchemy_session_factory(self):
        if self._sqlalchemy_session_factory is None:
            orm_module = self._load_sqlalchemy_modules()["orm"]
            self._sqlalchemy_session_factory = orm_module.sessionmaker(
                bind=self._get_sqlalchemy_engine(),
                future=True,
                expire_on_commit=False,
            )
        return self._sqlalchemy_session_factory

    def _get_sqlalchemy_engine(self):
        if self._sqlalchemy_engine is None:
            engine_module = self._load_sqlalchemy_modules()["engine"]
            sqlalchemy = self._require_sqlalchemy()
            self._sqlalchemy_engine = sqlalchemy.create_engine(
                engine_module.URL.create("mssql+pyodbc", query={"odbc_connect": self.connection_string}),
                future=True,
                use_setinputsizes=False,
            )
            sqlalchemy.event.listen(self._sqlalchemy_engine, "connect", self._on_sqlalchemy_connect)
        return self._sqlalchemy_engine

    def _on_sqlalchemy_connect(self, dbapi_connection, connection_record):
        del connection_record
        self._apply_session_context(dbapi_connection)

    def _parse_table_name(self, configured_table_name):
        parts = [part.strip().strip("[]") for part in configured_table_name.split(".") if part.strip()]
        if len(parts) == 1:
            return None, parts[0]
        if len(parts) == 2:
            return parts[0], parts[1]
        if len(parts) == 3:
            return parts[1], parts[2]
        raise ValueError(f"Nome tabella non valido: {configured_table_name}")

    def _reflect_table(self, configured_table_name):
        sqlalchemy = self._require_sqlalchemy()
        schema_name, table_name = self._parse_table_name(configured_table_name)
        metadata = sqlalchemy.MetaData()
        return sqlalchemy.Table(table_name, metadata, schema=schema_name, autoload_with=self._get_sqlalchemy_engine())

    def _get_soci_repository(self):
        if self._soci_repository is None:
            self._soci_repository = SociRepository(self)
        return self._soci_repository

    def _get_socio_datasharing_repository(self):
        if self._socio_datasharing_repository is None:
            self._socio_datasharing_repository = SocioDataSharingRepository(self)
        return self._socio_datasharing_repository
    
    def _get_tabella_logging_windows(self):
        if self._tabella_logging_windows is None:
            self._tabella_logging_windows = TabellaLoggingRepository(self)
        return self._tabella_logging_windows


    @staticmethod
    def _merge_socio_with_relation(socio_data, relation_row):
        if socio_data is None or socio_data.empty or not relation_row:
            return socio_data

        merged = socio_data.copy()
        first_index = merged.index[0]
        for column_name, column_value in relation_row.items():
            merged.loc[first_index, column_name] = column_value
        return merged

    # def _get_coca_cola_tracking_repository(self, tracking_config=None):
    #     if self._coca_cola_tracking_repository is None:
    #         # self._coca_cola_tracking_repository = CocaColaTrackingRepository(self, tracking_config)
    #     return self._coca_cola_tracking_repository

    def add_coca_cola_tracking_entry(self, values, tracking_config=None):
        entry_values = dict(values)
        entry_values.setdefault("created_at", datetime.now())
        repository = self._get_coca_cola_tracking_repository(tracking_config)
        try:
            repository.upsert_entry(entry_values)
        except ModuleNotFoundError:
            column_names = repository.column_mapping
            table_name = f"{repository.table_schema}.{repository.table_name}"
            upsert_query = f"""
                UPDATE {table_name}
                SET
                    [{column_names['socio_polo']}] = ?,
                    [{column_names['wholesaler_id']}] = ?,
                    [{column_names['log']}] = CASE
                        WHEN NULLIF([{column_names['log']}], '') IS NULL THEN ?
                        WHEN NULLIF(?, '') IS NULL THEN [{column_names['log']}]
                        ELSE [{column_names['log']}] + '  ' + ?
                    END,
                    [{column_names['created_at']}] = ?
                WHERE [{column_names['socio_code']}] = ?
                                    AND [{column_names['socio_polo']}] = ?
                                    AND [{column_names['wholesaler_id']}] = ?
                  AND [{column_names['period']}] = ?
                  AND [{column_names['flow_number']}] = ?;

                IF @@ROWCOUNT = 0
                BEGIN
                    INSERT INTO {table_name} (
                        [{column_names['socio_code']}],
                        [{column_names['socio_polo']}],
                        [{column_names['wholesaler_id']}],
                        [{column_names['period']}],
                        [{column_names['flow_number']}],
                        [{column_names['log']}],
                        [{column_names['created_at']}]
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                END
            """
            self.execute_non_query(
                upsert_query,
                [
                    entry_values.get("socio_polo"),
                    entry_values.get("wholesaler_id"),
                    entry_values.get("log"),
                    entry_values.get("log"),
                    entry_values.get("log"),
                    entry_values.get("created_at"),
                    entry_values.get("socio_code"),
                    entry_values.get("socio_polo"),
                    entry_values.get("wholesaler_id"),
                    entry_values.get("period"),
                    entry_values.get("flow_number"),
                    entry_values.get("socio_code"),
                    entry_values.get("socio_polo"),
                    entry_values.get("wholesaler_id"),
                    entry_values.get("period"),
                    entry_values.get("flow_number"),
                    entry_values.get("log"),
                    entry_values.get("created_at"),
                ],
            )

    def verify_socio(self, socio, datasharing_code=None):
        try:
            socio_data = self._get_soci_repository().get_active_socio_dataframe(socio)
            if datasharing_code:
                relation_row = self.get_socio_datasharing_relation(socio, datasharing_code)
                socio_data = self._merge_socio_with_relation(socio_data, relation_row)
            return socio_data
        except Exception as exc:
            self._log_error(f"Error verifying socio {socio}: {exc}")
            return pd.DataFrame()
        
    def get_logging_dataframe(self, cod_socio=None, cod_datasharing=None, num_periodo=None, cod_stato=None, tms_invio=None):
        """
        Restituisce un DataFrame pandas con i log filtrati per i parametri forniti tramite TabellaLoggingWindows.
        """
        try:
            return self._get_tabella_logging_windows().get_dataframe(
                cod_socio=cod_socio,
                cod_datasharing=cod_datasharing,
                num_periodo=num_periodo,
                cod_stato=cod_stato,
                tms_invio=tms_invio
            )
        except Exception as exc:
            self._log_error(f"Error fetching logging data with filters: {exc}")
            return pd.DataFrame([])

    def get_socio_datasharing_relations(self, socio=None, datasharing_code=None, only_enabled=False, only_current_tool=False):
        try:
            return self._get_socio_datasharing_repository().get_relations_dataframe(
                socio_code=socio,
                datasharing_code=datasharing_code,
                only_enabled=only_enabled,
                only_current_tool=only_current_tool,
            )
        except Exception as exc:
            self._log_error(
                f"Error reading socio-datasharing relations for socio={socio}, datasharing={datasharing_code}: {exc}"
            )
            return pd.DataFrame()

    def get_socio_datasharing_relation(self, socio, datasharing_code):
        relation_data = self.get_socio_datasharing_relations(socio=socio, datasharing_code=datasharing_code)
        if relation_data.empty:
            return {}

        relation_row = relation_data.iloc[0]
        if hasattr(relation_row, "to_dict"):
            return relation_row.to_dict()
        return dict(relation_row)

    def set_socio_datasharing_enabled(self, socio, datasharing_code, is_enabled, socio_name=None, datasharing_name=None):
        normalized_socio = str(socio).strip()
        normalized_datasharing = str(datasharing_code).strip()
        normalized_socio_name = str(socio_name or "").strip()
        normalized_datasharing_name = str(datasharing_name or "").strip()

        try:
            return self._get_socio_datasharing_repository().set_relation_enabled(
                normalized_socio,
                normalized_datasharing,
                bool(is_enabled),
                socio_name=normalized_socio_name,
                datasharing_name=normalized_datasharing_name,
            )
        except ModuleNotFoundError:
            relation_row = self.get_socio_datasharing_relation(normalized_socio, normalized_datasharing)
            now_value = datetime.now()

            if relation_row:
                update_query = """
                    UPDATE [cda].[dbo].[TR_Soci_DataSharing]
                    SET [Flag_Attivo] = ?,
                        [DataAggiornamento] = ?,
                        [TC_Soci_Ragione_Sociale] = CASE WHEN ? = '' THEN [TC_Soci_Ragione_Sociale] ELSE ? END,
                        [DataSharing_Nome] = CASE WHEN ? = '' THEN [DataSharing_Nome] ELSE ? END
                    WHERE [TC_Soci_Codice] = ? AND [DataSharing_Code] = ?
                """
                self.execute_non_query(
                    update_query,
                    [
                        int(bool(is_enabled)),
                        now_value,
                        normalized_socio_name,
                        normalized_socio_name,
                        normalized_datasharing_name,
                        normalized_datasharing_name,
                        normalized_socio,
                        normalized_datasharing,
                    ],
                )
                return True

            insert_query = """
                INSERT INTO [cda].[dbo].[TR_Soci_DataSharing] (
                    [TC_Soci_Codice],
                    [TC_Soci_Ragione_Sociale],
                    [DataSharing_Code],
                    [DataSharing_Nome],
                    [WholesalerID],
                    [Flag_Attivo],
                    [Flag_Usa_Nuovo_Strumento],
                    [DataAggiornamento]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_non_query(
                insert_query,
                [
                    normalized_socio,
                    normalized_socio_name,
                    normalized_datasharing,
                    normalized_datasharing_name,
                    "",
                    int(bool(is_enabled)),
                    0,
                    now_value,
                ],
            )
            return True

    def set_socio_datasharing_tool_enabled(self, socio, datasharing_code, use_new_tool, socio_name=None, datasharing_name=None):
        normalized_socio = str(socio).strip()
        normalized_datasharing = str(datasharing_code).strip()
        normalized_socio_name = str(socio_name or "").strip()
        normalized_datasharing_name = str(datasharing_name or "").strip()

        try:
            return self._get_socio_datasharing_repository().set_relation_tool_mode(
                normalized_socio,
                normalized_datasharing,
                bool(use_new_tool),
                socio_name=normalized_socio_name,
                datasharing_name=normalized_datasharing_name,
            )
        except ModuleNotFoundError:
            relation_row = self.get_socio_datasharing_relation(normalized_socio, normalized_datasharing)
            now_value = datetime.now()

            if relation_row:
                update_query = """
                    UPDATE [cda].[dbo].[TR_Soci_DataSharing]
                    SET [Flag_Usa_Nuovo_Strumento] = ?,
                        [DataAggiornamento] = ?,
                        [TC_Soci_Ragione_Sociale] = CASE WHEN ? = '' THEN [TC_Soci_Ragione_Sociale] ELSE ? END,
                        [DataSharing_Nome] = CASE WHEN ? = '' THEN [DataSharing_Nome] ELSE ? END
                    WHERE [TC_Soci_Codice] = ? AND [DataSharing_Code] = ?
                """
                self.execute_non_query(
                    update_query,
                    [
                        int(bool(use_new_tool)),
                        now_value,
                        normalized_socio_name,
                        normalized_socio_name,
                        normalized_datasharing_name,
                        normalized_datasharing_name,
                        normalized_socio,
                        normalized_datasharing,
                    ],
                )
                return True

            insert_query = """
                INSERT INTO [cda].[dbo].[TR_Soci_DataSharing] (
                    [TC_Soci_Codice],
                    [TC_Soci_Ragione_Sociale],
                    [DataSharing_Code],
                    [DataSharing_Nome],
                    [WholesalerID],
                    [Flag_Attivo],
                    [Flag_Usa_Nuovo_Strumento],
                    [DataAggiornamento]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_non_query(
                insert_query,
                [
                    normalized_socio,
                    normalized_socio_name,
                    normalized_datasharing,
                    normalized_datasharing_name,
                    "",
                    0,
                    int(bool(use_new_tool)),
                    now_value,
                ],
            )
            return True

    def update_socio_datasharing_configuration(
        self,
        socio,
        datasharing_code,
        use_new_tool,
        wholesaler_id=None,
        socio_name=None,
        datasharing_name=None,
    ):
        normalized_socio = str(socio).strip()
        normalized_datasharing = str(datasharing_code).strip()
        normalized_socio_name = str(socio_name or "").strip()
        normalized_datasharing_name = str(datasharing_name or "").strip()
        normalized_wholesaler_id = str(wholesaler_id or "").strip()

        try:
            return self._get_socio_datasharing_repository().update_relation_configuration(
                normalized_socio,
                normalized_datasharing,
                bool(use_new_tool),
                wholesaler_id=normalized_wholesaler_id,
                socio_name=normalized_socio_name,
                datasharing_name=normalized_datasharing_name,
            )
        except ModuleNotFoundError:
            relation_row = self.get_socio_datasharing_relation(normalized_socio, normalized_datasharing)
            now_value = datetime.now()

            if relation_row:
                update_query = """
                    UPDATE [cda].[dbo].[TR_Soci_DataSharing]
                    SET [Flag_Usa_Nuovo_Strumento] = ?,
                        [WholesalerID] = ?,
                        [DataAggiornamento] = ?,
                        [TC_Soci_Ragione_Sociale] = CASE WHEN ? = '' THEN [TC_Soci_Ragione_Sociale] ELSE ? END,
                        [DataSharing_Nome] = CASE WHEN ? = '' THEN [DataSharing_Nome] ELSE ? END
                    WHERE [TC_Soci_Codice] = ? AND [DataSharing_Code] = ?
                """
                self.execute_non_query(
                    update_query,
                    [
                        int(bool(use_new_tool)),
                        normalized_wholesaler_id,
                        now_value,
                        normalized_socio_name,
                        normalized_socio_name,
                        normalized_datasharing_name,
                        normalized_datasharing_name,
                        normalized_socio,
                        normalized_datasharing,
                    ],
                )
                return True

            insert_query = """
                INSERT INTO [cda].[dbo].[TR_Soci_DataSharing] (
                    [TC_Soci_Codice],
                    [TC_Soci_Ragione_Sociale],
                    [DataSharing_Code],
                    [DataSharing_Nome],
                    [WholesalerID],
                    [Flag_Attivo],
                    [Flag_Usa_Nuovo_Strumento],
                    [DataAggiornamento]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.execute_non_query(
                insert_query,
                [
                    normalized_socio,
                    normalized_socio_name,
                    normalized_datasharing,
                    normalized_datasharing_name,
                    normalized_wholesaler_id,
                    0,
                    int(bool(use_new_tool)),
                    now_value,
                ],
            )
            return True

    def uses_current_tool_for_datasharing(self, socio, datasharing_code):
        relation_data = self.get_socio_datasharing_relations(socio=socio, datasharing_code=datasharing_code)
        if relation_data.empty:
            return False
        return bool(int(relation_data.iloc[0].get("Flag_Usa_Nuovo_Strumento", 0) or 0))

    def is_socio_enabled_for_datasharing(self, socio, datasharing_code):
        relation_data = self.get_socio_datasharing_relations(socio=socio, datasharing_code=datasharing_code)
        if relation_data.empty:
            return False
        row = relation_data.iloc[0]
        return bool(int(row.get("Flag_Attivo", 0) or 0)) and bool(int(row.get("Flag_Usa_Nuovo_Strumento", 0) or 0))

    def get_enabled_datasharing_codes_for_socio(self, socio):
        relation_data = self.get_socio_datasharing_relations(socio=socio, only_enabled=True, only_current_tool=True)
        if relation_data.empty:
            return []

        codes = []
        for _, row in relation_data.iterrows():
            code = str(row.get("DataSharing_Code", "")).strip()
            if code and code not in codes:
                codes.append(code)
        return codes

    def get_datasharing_codes_for_current_tool(self):
        relation_data = self.get_socio_datasharing_relations(only_current_tool=True)
        if relation_data.empty:
            return []

        codes = []
        for _, row in relation_data.iterrows():
            code = str(row.get("DataSharing_Code", "") or "").strip()
            if code and code not in codes:
                codes.append(code)
        return codes

    def get_enabled_soci_for_datasharing(self, datasharing_code):
        relation_data = self.get_socio_datasharing_relations(
            datasharing_code=datasharing_code,
            only_enabled=True,
            only_current_tool=True,
        )
        if relation_data.empty:
            return []

        soci_rows = []
        for _, row in relation_data.iterrows():
            socio_code = str(row.get("TC_Soci_Codice", "")).strip()
            if not socio_code:
                continue

            soci_rows.append(
                {
                    "code": socio_code,
                    "name": str(row.get("TC_Soci_Ragione_Sociale", "")).strip(),
                }
            )

        return soci_rows
    def leggo_sociperiodo_attivi(self):
            """
            Restituisce un DataFrame con i record di TD_RPT_SOCIO_PERIODO con COD_STATO 'INS' o 'RUN' e sottoscrizione attiva (COD_STATO='A' in TA_SOTTOSCRIZIONI_RPT).
            Chiama i repository SottoscrizioniRptRepository e TdRptSocioPeriodoRepository.
            """
            from .repositories.sottoscrizioni_rpt_repository import SottoscrizioniRptRepository
            from .repositories.td_rpt_socio_periodo_repository import TdRptSocioPeriodoRepository

            sottoscrizioni_repo = SottoscrizioniRptRepository(self)
            sottoscrizioni_attive = sottoscrizioni_repo.get_dataframe(cod_stato='A')
            if sottoscrizioni_attive.empty:
                self._log_info("Nessuna sottoscrizione attiva trovata in TA_SOTTOSCRIZIONI_RPT.")
                return None
            codici_attivi = set(sottoscrizioni_attive['COD_SOTTOSCRIZIONE'])

            td_rpt_repo = TdRptSocioPeriodoRepository(self)
            df = td_rpt_repo.get_dataframe()
            df = df[df['COD_STATO'].isin(['INS', 'RUN'])]
            df = df[df['COD_SOTTOSCRIZIONE'].isin(codici_attivi)]
            if df.empty:
                self._log_info("Nessuna riga trovata in TD_RPT_SOCIO_PERIODO con sottoscrizione attiva.")
                return None
            return df.reset_index(drop=True)
