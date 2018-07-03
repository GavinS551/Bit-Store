import os
import pathlib
import json


DATA_DIR = os.path.join(pathlib.Path.home(), '.Bit-Store')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


DEFAULT_CONFIG = {

    'STANDARD_DATA_FORMAT': {
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
            'TXNS': {},
            'PRICE': 0.0,
            'WALLET_BAL': 0,
            'UNSPENT_OUTS': {}
    },

    # Sensitive data must be stored as a string due to limitations in data.py's
    # handling of sensitive data encryption
    'SENSITIVE_DATA': [
            'MNEMONIC',
            'XPRIV',
    ],

    'BIP32_PATHS': {
            'bip49path': "49'/0'/0'",
            'bip44path': "44'/0'/0'"
    },

    'PRICE_API_SOURCE': 'coinmarketcap',

    'BLOCKCHAIN_API_SOURCE': 'blockchain.info',

    'FIAT': 'USD',

    'UNITS': 'BTC'
}


def init():
    # creates program data dir if it doesn't exist
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    # and likewise for the config file itself
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w+') as cf:
            json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)


def read_file():
    with open(CONFIG_FILE, 'r') as c:
        return json.load(c)


def reset_config_file():
    with open(CONFIG_FILE, 'w') as cf:
        json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)


# def write_value(key, value):
#     if key not in DEFAULT_CONFIG:
#         raise ValueError(f'{key} is an invalid key')
#
#     config = read_file()
#     config[key] = value
#
#     with open(CONFIG_FILE, 'w') as cf:
#         json.dump(config, cf, indent=4, sort_keys=False)


init()
_CONFIG_VARS = read_file()


# CONFIG VARIABLES
STANDARD_DATA_FORMAT = _CONFIG_VARS['STANDARD_DATA_FORMAT']

SENSITIVE_DATA = _CONFIG_VARS['SENSITIVE_DATA']

BIP32_PATHS = _CONFIG_VARS['BIP32_PATHS']

PRICE_API_SOURCE = _CONFIG_VARS['PRICE_API_SOURCE']

BLOCKCHAIN_API_SOURCE = _CONFIG_VARS['BLOCKCHAIN_API_SOURCE']

FIAT = _CONFIG_VARS['FIAT']
