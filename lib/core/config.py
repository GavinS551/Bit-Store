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


@functools.lru_cache(maxsize=None)
def read_file():
    try:
        with open(CONFIG_FILE, 'r') as c:
            return json.load(c)
    except FileNotFoundError:
        # when config is imported, and there is no config file,
        # just use what will be dumped into it anyway on init() call
        return DEFAULT_CONFIG


def expected_type(key):
    if key not in DEFAULT_CONFIG:
        raise KeyError(f'{key} is an invalid key')

    return type(DEFAULT_CONFIG[key])


def write_values(**kwargs):
    config = read_file()

    for k, v in kwargs.items():

        if k not in DEFAULT_CONFIG:
            raise KeyError(f'{k} is an invalid key')

        if not isinstance(v, type(DEFAULT_CONFIG[k])):
            raise TypeError(f'{v} is of incorrect type. \'{type(DEFAULT_CONFIG[k])}\' is expected')

        config[k] = v

    data = json.dumps(config, indent=4, sort_keys=True)
    utils.atomic_file_write(data, CONFIG_FILE)


PRICE_API_SOURCE = read_file()['PRICE_API_SOURCE']

BLOCKCHAIN_API_SOURCE = read_file()['BLOCKCHAIN_API_SOURCE']

FIAT = read_file()['FIAT']

BTC_UNITS = read_file()['BTC_UNITS']

FONT = read_file()['FONT']

SPEND_UNCONFIRMED_UTXOS = read_file()['SPEND_UNCONFIRMED_UTXOS']

SPEND_UTXOS_INDIVIDUALLY = read_file()['SPEND_UTXOS_INDIVIDUALLY']

MAX_LOG_FILES_STORED = read_file()['MAX_LOG_FILES_STORED']

GUI_SHOW_FIAT_TX_HISTORY = read_file()['GUI_SHOW_FIAT_TX_HISTORY']
