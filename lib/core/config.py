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


def reset_config_file():
    with open(CONFIG_FILE, 'w') as cf:
        json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)


def write_value(key, value):
    if key not in DEFAULT_CONFIG:
        raise ValueError(f'{key} is an invalid key')

    config = read_file()
    config[key] = value

    data = json.dumps(config, indent=4, sort_keys=True)
    utils.atomic_file_write(data, CONFIG_FILE)


init()
_CONFIG_VARS = read_file()


# CONFIG VARIABLES FROM FILE

BIP32_PATHS = _CONFIG_VARS['BIP32_PATHS']

PRICE_API_SOURCE = _CONFIG_VARS['PRICE_API_SOURCE']

BLOCKCHAIN_API_SOURCE = _CONFIG_VARS['BLOCKCHAIN_API_SOURCE']

FIAT = _CONFIG_VARS['FIAT']

UNITS = _CONFIG_VARS['UNITS']

FONT = _CONFIG_VARS['FONT']

SPEND_UNCONFIRMED_UTXOS = _CONFIG_VARS['SPEND_UNCONFIRMED_UTXOS']

SPEND_UTXOS_INDIVIDUALLY = _CONFIG_VARS['SPEND_UTXOS_INDIVIDUALLY']
