from lib import logger
from lib.core import config
from lib.gui import gui_root


if __name__ == '__main__':
    root_logger = logger.get_logger()
    root_logger.info('Created root logger.')

    config.init()
    root_logger.info('Program initialised ( executed config.init() ).')

    root_logger.info('Starting gui_root mainloop.')
    gui_root.main()

    root_logger.info('Exiting gui_root mainloop.')
