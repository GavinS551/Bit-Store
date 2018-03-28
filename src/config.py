import pathlib
import os


DATA_DIR = os.path.join(pathlib.Path.home(), '.BTC-WALLET')

###############################################################################

STANDARD_DATA_FORMAT = {
        'MNEMONIC': None,
        'XPRIV': None,
        'XPUB': None,
        'PATH': None,
        'GAP_LIMIT': None,
        'ADDRESSES_RECEIVING': [],
        'ADDRESSES_CHANGE': [],
        'ADDRESSES_USED': [],
        'WIFKEYS_RECEIVING': [],
        'WIFKEYS_CHANGE': [],
        'WIFKEYS_USED': [],
        'BTC_PRICE': None

    }

SENSITIVE_DATA = ['MNEMONIC', 'XPRIV', 'WIFKEYS_RECEIVING', 'WIFKEYS_CHANGE', 'WIFKEYS_USED']

###############################################################################