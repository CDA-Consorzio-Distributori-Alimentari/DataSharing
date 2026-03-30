import pyodbc
from config import Config
import pandas as pd
from datetime import datetime
import importlib


class AutoExecutionRepository:
    def __init__(self, db_manager, auto_config):
        self.db_manager = db_manager
        self.auto_config = auto_config
        self.column_names = self._build_column_names(auto_config)
        self.session_factory = self.db_manager._get_sqlalchemy_session_factory()
        self.job_model = self._map_job_model(auto_config)

    def _build_column_names(self, auto_config):
        table_name = auto_config.get("table")
        if not table_name:
            raise ValueError("Configurazione auto_execution incompleta: manca 'table'.")

        return {
            "status": auto_config.get("status_column", "status"),
            "socio": auto_config.get("socio_column", "socio"),
            "period": auto_config.get("period_column", "periodo"),
            "datasharing": auto_config.get("datasharing_column", "datasharing"),
            "timestamp": auto_config.get("timestamp_column", "timestamp"),
            "filename": auto_config.get("filename_column", "filename"),
            "message": auto_config.get("message_column"),
            "order_by": auto_config.get("order_by_column", auto_config.get("period_column", "periodo")),
        }

    def _map_job_model(self, auto_config):
        job_table = self.db_manager._reflect_table(auto_config["table"])
        mapper_registry = self.db_manager._sqlalchemy_registry()

        class AutoExecutionJob:
            pass

        mapper_registry.map_imperatively(AutoExecutionJob, job_table)
        return AutoExecutionJob

    def _current_run_timestamp(self):
        return int(datetime.now().strftime("%Y%m%d%H%M%S"))

    def _get_attr(self, instance, logical_name):
        return getattr(instance, self.column_names[logical_name])

    def _set_attr(self, instance, logical_name, value):
        setattr(instance, self.column_names[logical_name], value)

    def claim_next_job(self):
        sqlalchemy = self.db_manager._require_sqlalchemy()
        pending_status = self.auto_config.get("status_pending", "INS")
        running_status = self.auto_config.get("status_running", "RUN")
        run_timestamp = self._current_run_timestamp()

        with self.session_factory.begin() as session:
            query = (
                session.query(self.job_model)
                .with_hint(self.job_model, "WITH (UPDLOCK, READPAST, ROWLOCK)", "mssql")
                .filter(getattr(self.job_model, self.column_names["status"]) == pending_status)
                .order_by(getattr(self.job_model, self.column_names["order_by"]))
            )
            job = query.first()
            if job is None:
                return None

            self._set_attr(job, "status", running_status)
            self._set_attr(job, "timestamp", run_timestamp)
            session.flush()

            return {
                "socio": self._get_attr(job, "socio"),
                "periodo": self._get_attr(job, "period"),
                "datasharing": self._get_attr(job, "datasharing"),
                "run_timestamp": self._get_attr(job, "timestamp"),
            }

    def complete_job(self, job_data, final_status, output_file=None, message=None):
        running_status = self.auto_config.get("status_running", "RUN")
        completed_timestamp = self._current_run_timestamp()

        with self.session_factory.begin() as session:
            query = (
                session.query(self.job_model)
                .filter(getattr(self.job_model, self.column_names["status"]) == running_status)
                .filter(getattr(self.job_model, self.column_names["socio"]) == job_data.get("socio"))
                .filter(getattr(self.job_model, self.column_names["period"]) == job_data.get("periodo"))
                .filter(getattr(self.job_model, self.column_names["datasharing"]) == job_data.get("datasharing"))
                .filter(getattr(self.job_model, self.column_names["timestamp"]) == job_data.get("run_timestamp"))
            )
            job = query.one_or_none()
            if job is None:
                raise ValueError("Job auto_execution non trovato durante il completamento.")

            self._set_attr(job, "status", final_status)
            self._set_attr(job, "timestamp", completed_timestamp)
            self._set_attr(job, "filename", output_file or "")
            if self.column_names["message"]:
                self._set_attr(job, "message", message or "")


class DBManager:
    def __init__(self, log_manager=None):
        # Retrieve the connection string from the Config class
        config = Config()
        self.connection_string = config.get_connection_string()

        # Initialize log manager
        self.log_manager = log_manager
        self._auto_execution_repository = None
        self._sqlalchemy_engine = None
        self._sqlalchemy_modules = None
        self._sqlalchemy_session_factory = None
        self._soci_table = None

    def execute_query(self, query, params=None):
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()
            # Fetch all results and convert to DataFrame
            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)

    def fetch_all(self, query, params=None):
        with pyodbc.connect(self.connection_string) as conn:
            # Use pandas to execute the query and return a DataFrame
            return pd.read_sql_query(query, conn, params=params)

    def fetch_one(self, query, params=None):
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            return cursor.fetchone()

    def execute_non_query(self, query, params=None):
        with pyodbc.connect(self.connection_string) as conn:
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
            )
        return self._sqlalchemy_engine

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

    def _get_soci_table(self):
        if self._soci_table is None:
            self._soci_table = self._reflect_table("cda.dbo.TC_Soci")
        return self._soci_table

    def _get_auto_execution_repository(self, auto_config):
        if self._auto_execution_repository is None:
            self._auto_execution_repository = AutoExecutionRepository(self, auto_config)
        return self._auto_execution_repository

    def claim_next_auto_job(self, auto_config):
        return self._get_auto_execution_repository(auto_config).claim_next_job()

    def complete_auto_job(self, auto_config, job, status, output_file=None, message=None):
        self._get_auto_execution_repository(auto_config).complete_job(job, status, output_file=output_file, message=message)
        
    def verify_socio(self, socio):
        """
        Verifies if a socio is active and retrieves their data sharing options.

        Args:
            socio (str): The socio code to verify.

        Returns:
            pd.DataFrame: A DataFrame containing the socio's data sharing options, or an empty DataFrame if invalid.
        """
        try:
            sqlalchemy = self._require_sqlalchemy()
            soci_table = self._get_soci_table()
            columns = [
                "TC_Soci_Codice",
                "TC_Tipo_Clientela_Codice",
                "TC_Soci_Ragione_Sociale",
                "TC_Soci_CocaCola_Attivo",
                "TC_Soci_CocaCola_Codice",
                "TC_Soci_CocaCola_In_Chiaro",
                "TC_Soci_SH",
                "TC_Soci_Campari_Attivo",
                "TC_Soci_Socio_Attivo",
                "TC_Soci_Ferrero_Attivo",
                "TC_Soci_DIAGEO_Attivo",
                "TC_Soci_RedBull_Attivo",
                "TC_Soci_Martini_Attivo",
            ]
            query = (
                sqlalchemy.select(*(soci_table.c[column] for column in columns))
                .where(soci_table.c.TC_Soci_Socio_Attivo == 1)
                .where(soci_table.c.TC_Soci_Codice == socio)
            )

            with self._get_sqlalchemy_engine().connect() as connection:
                result = pd.DataFrame(connection.execute(query).mappings().all())
        except ModuleNotFoundError:
            query = """
            SELECT [TC_Soci_Codice],
                   [TC_Tipo_Clientela_Codice],
                   [TC_Soci_Ragione_Sociale],
                   [TC_Soci_CocaCola_Attivo],
                   [TC_Soci_CocaCola_Codice],
                   [TC_Soci_CocaCola_In_Chiaro],
                   [TC_Soci_SH],
                   [TC_Soci_Campari_Attivo],
                   [TC_Soci_Socio_Attivo],
                   [TC_Soci_Ferrero_Attivo],
                   [TC_Soci_DIAGEO_Attivo],
                   [TC_Soci_RedBull_Attivo],
                   [TC_Soci_Martini_Attivo]
            FROM [cda].[dbo].[TC_Soci]
            WHERE [TC_Soci_Socio_Attivo] = 1 AND [TC_Soci_Codice] = ?
            """
            result = self.fetch_all(query, (socio,))

            # Check if the result is empty or has unexpected structure
            if result.empty or result.shape[1] != 13:
                if self.log_manager and hasattr(self.log_manager, "warning"):
                    self.log_manager.warning(f"Unexpected query result for socio {socio}.")
                return pd.DataFrame()  # Return an empty DataFrame if the result is invalid

            #self.log(f"Socio {socio} is active with data sharing options.")
            return result
        except Exception as e:
            # Log the error with detailed information
            if self.log_manager and hasattr(self.log_manager, "error"):
                self.log_manager.error(f"Error verifying socio {socio}: {str(e)}")
            return pd.DataFrame()

