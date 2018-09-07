import json
import functools

from . import utils
from ._config_vars import *


def init():
    """ should be first function called in the program """
    for dir_ in (DATA_DIR, WALLET_DATA_DIR, LOGGER_DIR):
        if not os.path.isdir(dir_):
            os.makedirs(dir_, exist_ok=True)

    # config file init
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as cf:
            json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)

    # add new config variables into the file
    missing_vars = set(DEFAULT_CONFIG) - {k for k in read_file() if k in DEFAULT_CONFIG}
    write_values(**{k: DEFAULT_CONFIG[k] for k in missing_vars})

    set_config_vars()


@functools.lru_cache(maxsize=None)
def read_file():
    with open(CONFIG_FILE, 'r') as c:
        return json.load(c)


def write_values(**kwargs):
    config = read_file()

    for k, v in kwargs.items():

        if k not in DEFAULT_CONFIG:
            raise ValueError(f'{k} is an invalid key')

        config[k] = v

    data = json.dumps(config, indent=4, sort_keys=True)
    utils.atomic_file_write(data, CONFIG_FILE)


def set_config_vars():
    for k, v in read_file().items():
        globals()[k] = v
