import json

class Config:
    def __init__(self):
        # Define config_file path
        config_file = "config.json"
        # Load placeholders from config.json
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
        # Read output_path from config.json or use default
        return self._output_path or "C:\\Users\\gabriele.chiarillo.CDA\\source\\repos\\DataSharing\\OutPut"

    def config_date_format(self):
        return getattr(self, '_config_date_format', None)

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
    
    def load_config(self):
        with open(self.configs_file, "r") as file:
            config_data = json.load(file)
        self._output_path = config_data.get("output_path", "C:\\Users\\gabriele.chiarillo.CDA\\source\\repos\\DataSharing\\OutPut") 
        self._db_path = config_data.get("db_path", "data_sharing.db")
        self._log_file = config_data.get("log_file", "data_sharing.log")
        self._ftp_config = config_data.get("ftp_config", {
            "host": "ftp.example.com",
            "user": "ftp_user",
            "password": "ftp_password"
        })
        self._mail_config = config_data.get("mail_config", {
            "smtp_server": "smtp.example.com",
            "port": 587,
            "user": "email_user",
            "password": "email_password"
        })
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
            "database": connection_string.get("database", "DATABASE")
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
        # Define config_file path
        config_file = "config.json"
        # Load placeholders from config.json
        with open(config_file, "r") as file:
            config_data = json.load(file)
        self.placeholders = config_data.get("placeholders", {})

