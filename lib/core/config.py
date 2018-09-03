import json

from . import utils
from ._config_vars import *


def init():
    # creates program data dir if it doesn't exist
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    # and likewise for the config file itself
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as cf:
            json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)


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


init()
_CONFIG_VARS = read_file()


# CONFIG VARIABLES FROM FILE

BIP32_PATHS = _CONFIG_VARS['BIP32_PATHS']

PRICE_API_SOURCE = _CONFIG_VARS['PRICE_API_SOURCE']

BLOCKCHAIN_API_SOURCE = _CONFIG_VARS['BLOCKCHAIN_API_SOURCE']

FIAT = _CONFIG_VARS['FIAT']

BTC_UNITS = _CONFIG_VARS['BTC_UNITS']

FONT = _CONFIG_VARS['FONT']

SPEND_UNCONFIRMED_UTXOS = _CONFIG_VARS['SPEND_UNCONFIRMED_UTXOS']

SPEND_UTXOS_INDIVIDUALLY = _CONFIG_VARS['SPEND_UTXOS_INDIVIDUALLY']

MAX_LOG_FILES_STORED = _CONFIG_VARS['MAX_LOG_FILES_STORED']
