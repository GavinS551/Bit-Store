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

import multiprocessing

from lib import logger
from lib.core import config
from lib.gui import gui_root


if __name__ == '__main__':
    # PyInstaller fix
    multiprocessing.freeze_support()

    # making sure all program directories exist, and creating them otherwise.
    config.init()

    root_logger = logger.get_logger()
    root_logger.info('Created root logger.')

    try:
        root_logger.info('Starting gui_root mainloop.')
        gui_root.main()

        root_logger.info('Exiting gui_root mainloop.')

    except BaseException:
        root_logger.exception(msg='Unhandled Exception -')
        raise
