import logging
from pathlib import Path


class LogManager:
    def __init__(self, log_file=None, level=None):
        if log_file is None or level is None:
            config_log_file, config_level = self._load_config_defaults()
            log_file = log_file or config_log_file
            level = level if level is not None else config_level

        self.logger = logging.getLogger("DataSharing")
        self.logger.setLevel(level)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        if not self.logger.handlers:
            resolved_log_file = self._resolve_log_file(log_file)
            file_handler = logging.FileHandler(resolved_log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        self._configure_console_handler(level, formatter)

    @staticmethod
    def _load_config_defaults():
        try:
            from services.config import Config

            config = Config()
            return config.log_file, config.log_level
        except Exception:
            return "application.log", logging.INFO

    @staticmethod
    def _default_log_file():
        project_root = Path(__file__).resolve().parent.parent
        log_dir = project_root / "LOG"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir / "application.log"

    @classmethod
    def _resolve_log_file(cls, log_file):
        log_path = Path(log_file)
        if log_path.parent == Path("."):
            default_log_file = cls._default_log_file()
            return default_log_file.with_name(log_path.name)

        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            return log_path
        except OSError:
            return cls._default_log_file().with_name(log_path.name)

    def _configure_console_handler(self, level, formatter):
        console_handlers = [
            handler for handler in self.logger.handlers
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)
        ]

        if level <= logging.DEBUG:
            if not console_handlers:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            return

        for handler in console_handlers:
            self.logger.removeHandler(handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    def log(self, message):
        self.info(message)

    def log_debug(self, message):
        self.debug(message)

    def log_info(self, message):
        self.info(message)

    def log_warning(self, message):
        self.warning(message)

    def log_error(self, message):
        self.error(message)