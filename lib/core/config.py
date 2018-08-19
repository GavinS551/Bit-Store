import os
import pathlib
import platform
import json

from . import utils


if platform.system() == 'Windows':
    DATA_DIR = os.path.join(os.environ['APPDATA'], 'Bit-Store')
else:
    DATA_DIR = os.path.join(pathlib.Path.home(), '.Bit-Store')

CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


DEFAULT_CONFIG = {

    'BIP32_PATHS': {
        'bip49path': "49'/0'/0'",
        'bip44path': "44'/0'/0'"
    },

    'PRICE_API_SOURCE': 'coinmarketcap',

    'BLOCKCHAIN_API_SOURCE': 'blockchain.info',

    'FIAT': 'USD',

    'UNITS': 'BTC',

    'FONT': 'verdana',

    'SPEND_UNCONFIRMED_UTXOS': False,

    'SPEND_UTXOS_INDIVIDUALLY': False
}


STANDARD_DATA_FORMAT = {
    'MNEMONIC': '',
    'XPRIV': '',
    'XPUB': '',
    'PATH': '',
    'GAP_LIMIT': 0,
    'SEGWIT': True,
    'ADDRESSES_RECEIVING': [],
    'ADDRESSES_CHANGE': [],
    'ADDRESSES_USED': [],
    'ADDRESS_BALS': {},
    'TXNS': [],
    'PRICE': 0.0,
    'WALLET_BAL': [],
    'UNSPENT_OUTS': [],
    'PASSWORD_HASH': '',
    'ADDRESS_WIF_KEYS': {}
}


# Sensitive data must be stored as a string or dict due to limitations in data.py's
# handling of sensitive data encryption
SENSITIVE_DATA = [
    'MNEMONIC',
    'XPRIV',
    'ADDRESS_WIF_KEYS'
]


# amounts satoshis have to be multiplied by to get other units
UNIT_FACTORS = {
    'BTC': 1e8,
    'mBTC': 1e5,
    'bits': 100,
    'sat': 1
}


UNITS_MAX_DECIMAL_PLACES = {
    'BTC': 8,
    'mBTC': 5,
    'bits': 2,
    'sat': 0
}


# standard format for datetime stings
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


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
# unlike above variables, these are meant to be changed by the user

for k, v in _CONFIG_VARS.items():
    vars()[k.upper()] = v
