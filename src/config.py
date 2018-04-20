import os
import pathlib
import json


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
            'PRICE': 0,
            'WALLET_BAL': 0
    },

    'SENSITIVE_DATA': [
            'MNEMONIC',
            'XPRIV',
    ],

    'BIP32_PATHS': {
            'bip49path': "49'/0'/0'",
            'bip44path': "44'/0'/0'"
    },

    'PRICE_API_SOURCE': 'coinmarketcap',

    'FIAT': 'USD'
}

DATA_DIR = os.path.join(pathlib.Path.home(), '.BTC-WALLET')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


# creates program data dir if it doesn't exist
if not os.path.isdir(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)


# and likewise for the config file itself
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w+') as cf:
        json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)


with open(CONFIG_FILE, 'r') as cf:
    CONFIG_VARS = json.load(cf)


# CONFIG VARIABLES
STANDARD_DATA_FORMAT = CONFIG_VARS['STANDARD_DATA_FORMAT']

SENSITIVE_DATA = CONFIG_VARS['SENSITIVE_DATA']

BIP32_PATHS = CONFIG_VARS['BIP32_PATHS']

PRICE_API_SOURCE = CONFIG_VARS['PRICE_API_SOURCE']

FIAT = CONFIG_VARS['FIAT']
