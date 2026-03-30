from log_manager import LogManager


class OutputManager:
    def __init__(self, log_manager=None):
        self.log = log_manager or LogManager()

    def log_info(self, message):
        self.log.log_info(message)

    def log_error(self, message):
        self.log.log_error(message)

    def log_warning(self, message):
        self.log.log_warning(message)