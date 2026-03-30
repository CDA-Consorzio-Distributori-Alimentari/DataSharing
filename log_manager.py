import logging

class LogManager:
    def __init__(self, log_file="application.log", level=logging.INFO):
        self.logger = logging.getLogger("DataSharing")
        self.logger.setLevel(level)

        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(file_handler)

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