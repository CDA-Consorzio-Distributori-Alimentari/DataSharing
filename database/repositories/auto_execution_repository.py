from datetime import datetime

from .base_repository import BaseRepository


class AutoExecutionRepository(BaseRepository):
    def __init__(self, db_manager, auto_config):
        self.auto_config = auto_config
        self.column_names = self._build_column_names(auto_config)
        self.ID_FIELD = self.column_names["timestamp"]
        super().__init__(db_manager)

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

    def _map_model(self):
        job_table = self.db_manager._reflect_table(self.auto_config["table"])
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
        pending_status = self.auto_config.get("status_pending", "INS")
        running_status = self.auto_config.get("status_running", "RUN")
        run_timestamp = self._current_run_timestamp()

        with self.session_factory.begin() as session:
            query = (
                session.query(self.model)
                .with_hint(self.model, "WITH (UPDLOCK, READPAST, ROWLOCK)", "mssql")
                .filter(getattr(self.model, self.column_names["status"]) == pending_status)
                .order_by(getattr(self.model, self.column_names["order_by"]))
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
        job = self.update_by_filters(
            {
                self.column_names["status"]: running_status,
                self.column_names["socio"]: job_data.get("socio"),
                self.column_names["period"]: job_data.get("periodo"),
                self.column_names["datasharing"]: job_data.get("datasharing"),
                self.column_names["timestamp"]: job_data.get("run_timestamp"),
            },
            {
                self.column_names["status"]: final_status,
                self.column_names["timestamp"]: completed_timestamp,
                self.column_names["filename"]: output_file or "",
                **({self.column_names["message"]: message or ""} if self.column_names["message"] else {}),
            },
        )
        if job is None:
            raise ValueError("Job auto_execution non trovato durante il completamento.")
