import importlib
from datetime import datetime

import pandas as pd
import pyodbc

from services.config import Config
from .repositories import CocaColaTrackingRepository, SociRepository


class DBManager:
    def __init__(self, log_manager=None):
        config = Config()
        self.connection_string = config.get_connection_string()
        self.log_manager = log_manager
        self._sqlalchemy_engine = None
        self._sqlalchemy_modules = None
        self._sqlalchemy_session_factory = None
        self._soci_repository = None
        self._coca_cola_tracking_repository = None

    def _log_warning(self, message):
        if self.log_manager is not None:
            self.log_manager.warning(message)

    def _log_error(self, message):
        if self.log_manager is not None:
            self.log_manager.error(message)

    def execute_query(self, query, params=None):
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()
            columns = [column[0] for column in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)

    def _fetch_all_with_pyodbc(self, query, params=None):
        with pyodbc.connect(self.connection_string) as conn:
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
                use_setinputsizes=False,
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

    def _get_soci_repository(self):
        if self._soci_repository is None:
            self._soci_repository = SociRepository(self)
        return self._soci_repository

    def _get_coca_cola_tracking_repository(self, tracking_config=None):
        if self._coca_cola_tracking_repository is None:
            self._coca_cola_tracking_repository = CocaColaTrackingRepository(self, tracking_config)
        return self._coca_cola_tracking_repository

    def add_coca_cola_tracking_entry(self, values, tracking_config=None):
        entry_values = dict(values)
        entry_values.setdefault("created_at", datetime.now())
        repository = self._get_coca_cola_tracking_repository(tracking_config)
        try:
            repository.upsert_entry(entry_values)
        except ModuleNotFoundError:
            column_names = repository.column_names
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

    def verify_socio(self, socio):
        try:
            return self._get_soci_repository().get_active_socio_dataframe(socio)
        except Exception as exc:
            self._log_error(f"Error verifying socio {socio}: {exc}")
            return pd.DataFrame()
