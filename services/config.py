import json
import logging
from pathlib import Path


class Config:
    def __init__(self):
        config_file = "config.json"
        with open(config_file, "r") as file:
            config_data = json.load(file)
        self.placeholders = config_data.get("placeholders", {})
        self.configs_file = "config.json"
        self.load_config()

    @property
    def db_path(self):
        return self._db_path

    @property
    def output_path(self):
        return self._output_path

    @property
    def working_folder(self):
        return self._working_folder

    @property
    def artifacts_root_path(self):
        return self._artifacts_root_path

    @property
    def shared_root_path(self):
        return self._artifacts_root_path

    @property
    def template_path(self):
        return self._template_path

    @property
    def querysql_path(self):
        return self._querysql_path

    def config_date_format(self):
        return getattr(self, "_config_date_format", None)

    @property
    def ftp_config(self):
        return self._ftp_config

    @property
    def mail_config(self):
        return self._mail_config

    @property
    def log_file(self):
        return self._log_file

    @property
    def log_folder(self):
        return self._log_folder

    @property
    def log_name(self):
        return self._log_name

    @property
    def log_level(self):
        return self._log_level

    @property
    def connection_string(self):
        return self._connection_string

    @property
    def connection_string_data_source(self):
        return self._connection_string["data_source"]

    @property
    def connection_string_integrated_security(self):
        return self._connection_string["integrated_security"]

    @property
    def connection_string_persist_security_info(self):
        return self._connection_string["persist_security_info"]

    @property
    def connection_string_pooling(self):
        return self._connection_string["pooling"]

    @property
    def connection_string_multiple_active_result_sets(self):
        return self._connection_string["multiple_active_result_sets"]

    @property
    def connection_string_encrypt(self):
        return self._connection_string["encrypt"]

    @property
    def connection_string_trust_server_certificate(self):
        return self._connection_string["trust_server_certificate"]

    @property
    def connection_string_command_timeout(self):
        return self._connection_string["command_timeout"]

    @property
    def auto_execution(self):
        return self._auto_execution

    def _get_project_root(self):
        return Path(__file__).resolve().parent.parent

    def _resolve_root_path(self, configured_root_path):
        if configured_root_path:
            candidate = Path(configured_root_path)
            if not candidate.is_absolute():
                candidate = self._working_folder / candidate
            return candidate.resolve(strict=False)

        return self._working_folder

    def _resolve_path(self, configured_path, default_relative_path, base_path=None):
        base_path = base_path or self._working_folder
        if configured_path:
            candidate = Path(configured_path)
            if not candidate.is_absolute():
                candidate = Path(base_path) / candidate
            return candidate.resolve(strict=False)

        return (Path(base_path) / default_relative_path).resolve(strict=False)

    def _get_default_log_folder(self):
        return self._artifacts_root_path / "LOG"

    def _resolve_log_folder(self, log_folder):
        default_log_folder = self._get_default_log_folder()
        if not log_folder:
            return default_log_folder

        candidate = Path(log_folder)
        if not candidate.is_absolute():
            candidate = self._artifacts_root_path / candidate

        return candidate.resolve(strict=False)

    def _ensure_directory(self, directory_path):
        Path(directory_path).mkdir(parents=True, exist_ok=True)

    def _ensure_artifact_structure(self, config_data):
        self._ensure_directory(self._artifacts_root_path)
        self._ensure_directory(self._output_path)
        self._ensure_directory(self._querysql_path)
        self._ensure_directory(self._template_path)
        self._ensure_directory(self._log_folder)

        for option_data in config_data.get("data_sharing_options", []):
            option_code = str(option_data.get("code", "")).strip()
            if not option_code:
                continue

            self._ensure_directory(Path(self._querysql_path) / option_code)

            if str(option_data.get("file_type", "")).lower() == "xml":
                self._ensure_directory(Path(self._template_path) / option_code)

    @staticmethod
    def _resolve_log_level(log_level):
        if isinstance(log_level, int):
            return log_level

        level_name = str(log_level or "INFO").upper()
        return getattr(logging, level_name, logging.INFO)

    def load_config(self):
        with open(self.configs_file, "r") as file:
            config_data = json.load(file)

        project_root = self._get_project_root()
        configured_working_folder = config_data.get("working_folder")
        if configured_working_folder:
            working_folder = Path(configured_working_folder)
            if not working_folder.is_absolute():
                working_folder = project_root / working_folder
            self._working_folder = working_folder.resolve(strict=False)
        else:
            self._working_folder = project_root

        configured_artifacts_root = config_data.get("artifacts_root_path", config_data.get("shared_root_path"))
        self._artifacts_root_path = self._resolve_root_path(configured_artifacts_root)

        self._template_path = str(
            self._resolve_path(config_data.get("template_path"), "templatexml", base_path=self._artifacts_root_path)
        )
        self._querysql_path = str(
            self._resolve_path(config_data.get("querysql_path"), "querysql", base_path=self._artifacts_root_path)
        )
        self._output_path = str(
            self._resolve_path(config_data.get("output_path"), "OutPut", base_path=self._artifacts_root_path)
        )
        self._db_path = config_data.get("db_path", "data_sharing.db")

        log_config = config_data.get("log", {})
        legacy_log_file = config_data.get("log_file")
        legacy_log_path = Path(legacy_log_file) if legacy_log_file else None
        configured_log_folder = log_config.get("folder", config_data.get("log_folder"))
        configured_log_name = log_config.get("name", config_data.get("log_name"))

        if not configured_log_folder and legacy_log_path and legacy_log_path.parent != Path("."):
            configured_log_folder = str(legacy_log_path.parent)

        default_log_name = "data_sharing.log"
        self._log_folder = str(self._resolve_log_folder(configured_log_folder))
        self._log_name = configured_log_name or (legacy_log_path.name if legacy_log_path else default_log_name)
        self._log_file = str(Path(self._log_folder) / self._log_name)
        self._log_level = self._resolve_log_level(log_config.get("level", config_data.get("log_level", "INFO")))
        self._ensure_artifact_structure(config_data)
        self._ftp_config = config_data.get(
            "ftp_config",
            {
                "host": "ftp.example.com",
                "user": "ftp_user",
                "password": "ftp_password",
            },
        )
        self._mail_config = config_data.get(
            "mail_config",
            {
                "smtp_server": "smtp.example.com",
                "port": 587,
                "user": "email_user",
                "password": "email_password",
            },
        )
        self._auto_execution = config_data.get("auto_execution", {})

        connection_string = config_data.get("connection_string", {})
        self._connection_string = {
            "data_source": connection_string.get("data_source", "DWH"),
            "integrated_security": connection_string.get("integrated_security", True),
            "persist_security_info": connection_string.get("persist_security_info", False),
            "pooling": connection_string.get("pooling", False),
            "multiple_active_result_sets": connection_string.get("multiple_active_result_sets", False),
            "encrypt": connection_string.get("encrypt", False),
            "trust_server_certificate": connection_string.get("trust_server_certificate", False),
            "command_timeout": connection_string.get("command_timeout", 0),
            "database": connection_string.get("database", "DATABASE"),
        }

    def get_data_sharing_options(self):
        with open(self.configs_file, "r") as file:
            return json.load(file)["data_sharing_options"]

    def get_connection_string(self):
        return (
            f"DRIVER={{SQL Server}};"
            f"SERVER={self._connection_string['data_source']};"
            f"Trusted_Connection={'yes' if self._connection_string['integrated_security'] else 'no'};"
            f"Persist Security Info={'yes' if self._connection_string['persist_security_info'] else 'no'};"
            f"Pooling={'yes' if self._connection_string['pooling'] else 'no'};"
            f"MultipleActiveResultSets={'yes' if self._connection_string['multiple_active_result_sets'] else 'no'};"
            f"Encrypt={'yes' if self._connection_string['encrypt'] else 'no'};"
            f"TrustServerCertificate={'yes' if self._connection_string['trust_server_certificate'] else 'no'};"
            f"DATABASE={self._connection_string['database']};"
        )

    def load_placeholders(self):
        config_file = "config.json"
        with open(config_file, "r") as file:
            config_data = json.load(file)
        self.placeholders = config_data.get("placeholders", {})