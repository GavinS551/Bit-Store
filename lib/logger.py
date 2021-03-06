# Copyright (C) 2018  Gavin Shaughnessy
#
# Bit-Store is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import datetime

from .core import config


def get_logger(log_to_file=True):
    """ if log_to_file is False, log to stderr """

    # create dir for log files if it doesn't exist
    if not os.path.isdir(config.LOGGER_DIR):
        os.makedirs(config.LOGGER_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt='%(asctime)s : %(levelname)s : %(module)s : %(message)s')

    if log_to_file:
        handler = _FileHandlerManager(log_dir=config.LOGGER_DIR,
                                      max_logs=config.get('MAX_LOG_FILES_STORED')).get_file_handler()

    else:
        handler = logging.StreamHandler()

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
            i = 0

            # to support multiple instances of the program running
            # (if one was left open for a while, and others were opened/closed,
            # the oldest log file may still be open in the python process)
            while i < len(self.logs):

                try:
                    os.remove(self.full_log_path(self.time_sorted_logs[i]))
                except PermissionError:
                    i += 1
                else:
                    break

        with open(full_path, 'w+'):
            pass

        return logging.FileHandler(self.full_log_path(name))
