import traceback

from lib import logger
from lib.core import config
from lib.gui import gui_root


if __name__ == '__main__':
    # making sure all program directories exist, and creating them otherwise.
    config.init()

    root_logger = logger.get_logger()
    root_logger.info('Created root logger.')

    try:
        root_logger.info('Starting gui_root mainloop.')
        gui_root.main()

        root_logger.info('Exiting gui_root mainloop.')

    except BaseException:
        root_logger.critical(traceback.format_exc())
        raise
