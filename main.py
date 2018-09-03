from lib.gui import gui_root
from lib import logger


if __name__ == '__main__':
    root_logger = logger.get_logger()
    root_logger.info('Created root logger.')

    root_logger.info('Starting gui_root mainloop.')
    gui_root.main()

    root_logger.info('Exiting gui_root mainloop.')
