# Copyright (C) 2018  Gavin Shaughnessy
#
# Bit-Store is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

""" config variables that aren't read from file are defined here, while
functions and other implementations of program configuration are done in
config.py
"""

import os
import platform
import pathlib


VERSION = '1.0'


if platform.system() == 'Windows':
    DATA_DIR = os.path.join(os.environ['APPDATA'], 'Bit-Store')
else:
    DATA_DIR = os.path.join(pathlib.Path.home(), '.Bit-Store')


WALLET_DATA_DIR = os.path.join(DATA_DIR, 'wallets')


CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')


LOGGER_DIR = os.path.join(DATA_DIR, 'logs')


DEFAULT_CONFIG = {

    'PRICE_API_SOURCE': 'coinmarketcap',

    'BLOCKCHAIN_API_SOURCE': 'blockchain.info',

    'FIAT': 'USD',

    'BTC_UNITS': 'BTC',

    'FONT': 'verdana',

    'SPEND_UNCONFIRMED_UTXOS': False,

    'SPEND_UTXOS_INDIVIDUALLY': False,

    'MAX_LOG_FILES_STORED': 10,

    'GUI_SHOW_FIAT_TX_HISTORY': True,

    'USE_LOCALTIME': True

}


STANDARD_DATA_FORMAT = {
    'MNEMONIC': str,
    'XPRIV': str,
    'XPUB': str,
    'ACCOUNT_XPUB': str,
    'PATH': str,
    'GAP_LIMIT': int,
    'SEGWIT': bool,
    'ADDRESSES_RECEIVING': list,
    'ADDRESSES_CHANGE': list,
    'ADDRESSES_USED': list,
    'ADDRESS_BALS': dict,
    'TXNS': list,
    'PRICE': float,
    'WALLET_BAL': list,
    'UNSPENT_OUTS': list,
    'PASSWORD_HASH': str,
    'ADDRESS_WIF_KEYS': dict,
    'DEFAULT_ADDRESSES': dict
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


BIP32_PATHS = {
    'bip49path': "49'/0'/0'",
    'bip44path': "44'/0'/0'"
}


# lowercase for comparisons
POSSIBLE_BTC_UNITS = ['BTC', 'mBTC', 'bits', 'sat']


POSSIBLE_FIAT_UNITS = ['AUD', 'CAD', 'EUR', 'GBP', 'JPY', 'USD']


POSSIBLE_BLOCKCHAIN_API_SOURCES = ['blockchain.info']


POSSIBLE_PRICE_API_SOURCES = ['coinmarketcap']


# standard format for datetime stings
DATETIME_FORMAT = '%Y-%m-%d %H:%M'


WALLET_DATA_FILE_NAME = 'wallet_data'


WALLET_INFO_FILE_NAME = 'w_info'
