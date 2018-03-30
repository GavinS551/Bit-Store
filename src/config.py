import pathlib
import os


DATA_DIR = os.path.join(pathlib.Path.home(), '.BTC-WALLET')

###############################################################################

STANDARD_DATA_FORMAT = {
        'MNEMONIC': '',
        'XPRIV': '',
        'XPUB': '',
        'PATH': '',
        'GAP_LIMIT': 0,
        'ADDRESSES_RECEIVING': [],
        'ADDRESSES_CHANGE': [],
        'ADDRESSES_USED': [],
        'WIFKEYS_RECEIVING': [],
        'WIFKEYS_CHANGE': [],
        'WIFKEYS_USED': []

    }

###############################################################################

BIP32_PATHS = {
        'bip49path': "49'/0'/0'",
        'bip44path': "44'/0'/0'"
    }