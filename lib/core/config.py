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
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as cf:
            json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)

    # add new config variables into the file
    missing_vars = set(DEFAULT_CONFIG.keys()) - {k for k in read_file()}
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


def get_value(key):
    try:
        return read_file()[key]
    except KeyError:
        if key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]
        else:
            raise


PRICE_API_SOURCE = get_value('PRICE_API_SOURCE')

BLOCKCHAIN_API_SOURCE = get_value('BLOCKCHAIN_API_SOURCE')

FIAT = get_value('FIAT')

BTC_UNITS = get_value('BTC_UNITS')

FONT = get_value('FONT')

SPEND_UNCONFIRMED_UTXOS = get_value('SPEND_UNCONFIRMED_UTXOS')

SPEND_UTXOS_INDIVIDUALLY = get_value('SPEND_UTXOS_INDIVIDUALLY')

MAX_LOG_FILES_STORED = get_value('MAX_LOG_FILES_STORED')

GUI_SHOW_FIAT_TX_HISTORY = get_value('GUI_SHOW_FIAT_TX_HISTORY')

USE_LOCALTIME = get_value('USE_LOCALTIME')
