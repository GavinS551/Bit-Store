""" config variables that aren't read from file are defined here, while
functions and other implementations of program configuration are done in
config.py
"""

import os
import platform
import pathlib


if platform.system() == 'Windows':
    DATA_DIR = os.path.join(os.environ['APPDATA'], 'Bit-Store')
else:
    DATA_DIR = os.path.join(pathlib.Path.home(), '.Bit-Store')


WALLET_DATA_DIR = os.path.join(DATA_DIR, 'wallets')


CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


LOGGER_DIR = os.path.join(DATA_DIR, 'logs')


DEFAULT_CONFIG = {

    'BIP32_PATHS': {
        'bip49path': "49'/0'/0'",
        'bip44path': "44'/0'/0'"
    },

    'PRICE_API_SOURCE': 'coinmarketcap',

    'BLOCKCHAIN_API_SOURCE': 'blockchain.info',

    'FIAT': 'USD',

    'BTC_UNITS': 'BTC',

    'FONT': 'verdana',

    'SPEND_UNCONFIRMED_UTXOS': False,

    'SPEND_UTXOS_INDIVIDUALLY': False,

    'MAX_LOG_FILES_STORED': 10,

    'GUI_SHOW_FIAT_TX_HISTORY': True

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
    'WALLET_BAL': [0, 0],
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


# lowercase for comparisons
POSSIBLE_BTC_UNITS = ['BTC', 'mBTC', 'bits', 'sat']


POSSIBLE_FIAT_UNITS = ['AUD', 'CAD', 'EUR', 'GBP', 'JPY', 'USD']


POSSIBLE_BLOCKCHAIN_API_SOURCES = ['blockchain.info']


POSSIBLE_PRICE_API_SOURCES = ['coinmarketcap']


# standard format for datetime stings
DATETIME_FORMAT = '%Y-%m-%d %H:%M'
