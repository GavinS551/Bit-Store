import logging
import os
import datetime

from .core import config


def get_logger():

    # create dir for log files if it doesn't exist
    if not os.path.isdir(config.LOGGER_DIR):
        os.makedirs(config.LOGGER_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt='%(asctime)s : %(levelname)s : %(module)s : %(message)s')

    handler = _FileHandlerManager(log_dir=config.LOGGER_DIR,
                                  max_logs=config.MAX_LOG_FILES_STORED).get_file_handler()
    handler.setFormatter(formatter)

    logger = logging.getLogger('root')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger


class _FileHandlerManager:
    """ log files are named starting with self.file_prefix, and appending
    a unix timestamp rounded to nearest second. Use the method get_file_handler
    to return a FileHandler object to be used with logging module
    """

    def __init__(self, log_dir, max_logs):
        self.log_dir = log_dir
        self.max_logs = max_logs

        self.file_prefix = 'LOG_'

        self.age_sorted_files = []

    def full_log_path(self, log):
        return os.path.join(self.log_dir, log)

    @property
    def logs(self):
        return [log for log in os.listdir(self.log_dir) if log.startswith(self.file_prefix)]

    @property
    def time_sorted_logs(self):

        def _sort_key(log):
            timestamp = int(log[len(self.file_prefix):])
            return timestamp

        return sorted(self.logs, key=_sort_key)

    def get_file_handler(self):
        name = self.file_prefix + str(round(datetime.datetime.now().timestamp()))
        full_path = self.full_log_path(name)

        # remove the oldest log file if there are more than max logs
        if len(self.logs) >= self.max_logs:
            os.remove(self.full_log_path(self.time_sorted_logs[0]))

        with open(full_path, 'w+'):
            pass

        return logging.FileHandler(self.full_log_path(name))
