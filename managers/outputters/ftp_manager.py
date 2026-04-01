from ftplib import FTP
from io import BytesIO
from pathlib import PurePosixPath

from ..log_manager import LogManager

class FTPManager:
    def __init__(self, option=None, host=None, username=None, password=None, port=None, log_manager=None):
        ftp_config = getattr(option, "config", None) if option is not None else None
        self.host = host or getattr(ftp_config, "host", None)
        self.username = username or getattr(ftp_config, "user", None)
        self.password = password or getattr(ftp_config, "password", None)
        self.port = port or getattr(ftp_config, "port", None)
        self.create_ok_file = getattr(ftp_config, "create_ok_file", False)
        self.log = log_manager or LogManager()

        missing_fields = []
        if not self.host:
            missing_fields.append("host")
        if not self.username:
            missing_fields.append("user")
        if not self.password:
            missing_fields.append("password")

        if missing_fields:
            missing_list = ", ".join(missing_fields)
            raise ValueError(f"Configurazione FTP incompleta nella option: campi mancanti {missing_list}")

    @staticmethod
    def _build_ok_file_name(file_name):
        remote_path = PurePosixPath(file_name)
        ok_name = f"{remote_path.stem}.ok" if remote_path.suffix else f"{remote_path.name}.ok"
        if str(remote_path.parent) in {"", "."}:
            return ok_name
        return str(remote_path.parent / ok_name)

    def upload_file(self, file_name, file_stream):
        try:
            self.log.info(f"Avvio upload FTP del file {file_name} verso host {self.host}.")
            with FTP() as ftp:
                ftp.connect(self.host, self.port or 21)
                ftp.login(self.username, self.password)
                if hasattr(file_stream, 'seek'):
                    file_stream.seek(0)
                ftp.storbinary(f'STOR {file_name}', file_stream)
                if self.create_ok_file:
                    ok_file_name = self._build_ok_file_name(file_name)
                    ftp.storbinary(f'STOR {ok_file_name}', BytesIO(b""))
                    self.log.info(f"Creato marker FTP {ok_file_name} dopo upload di {file_name}.")
            self.log.info(f"Upload FTP completato per il file {file_name}.")
        except Exception as exc:
            self.log.error(f"Errore durante upload FTP del file {file_name}: {exc}")
            raise