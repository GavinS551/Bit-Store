import os
import hashlib
import base64
import json
import tempfile

import cryptography.fernet as fernet

from src.bip32 import Bip32
import src.config as CONFIG


class Crypto:

    def __init__(self, password):
        self._fernet = fernet.Fernet(self.key_from_password(password))

    @staticmethod
    def key_from_password(password, iterations=100_000):
        """ Returns a key to be used with fernet encryption"""
        b_password = password.encode('utf-8')
        b_key = hashlib.pbkdf2_hmac('sha256', b_password, b'', iterations)
        return base64.urlsafe_b64encode(b_key)

    def encrypt(self, string):
        token = self._fernet.encrypt(string.encode('utf-8'))
        return token.decode('utf-8')

    def decrypt(self, token):
        string = self._fernet.decrypt(token.encode('utf-8'))
        return string.decode('utf-8')


class DataStore(Crypto):

    STANDARD_DATA_FORMAT = {
        'MNEMONIC': None,
        'XPRIV': None,
        'XPUB': None,
        'PATH': None,
        'GAP_LIMIT': None,
        'ADDRESSES': {
            'RECEIVING': [],
            'CHANGE': [],
            'USED': []
        },
        'WIP_KEYS': {
            'RECEIVING': [],
            'CHANGE': [],
            'USED': []
        }

    }

    def __init__(self, file_path, password, write_template=True):
        super().__init__(password)
        self.file_path = file_path
        self.file_dir = ''.join(os.path.split(file_path)[:-1])

        if not os.path.exists(self.file_path):
            raise Exception(f'File path:{self.file_path} doesn\'t exist!')

        if write_template:
            with open(self.file_path, 'r') as d:
                if d.read() == '':
                    self._write_template()

    @property
    def _data(self):
        with open(self.file_path, 'r') as d:
            return json.load(d)

    def _write_template(self):
        with open(self.file_path, 'w') as d:
            d.write(json.dumps(self.STANDARD_DATA_FORMAT))

    def write_value(self, **kwargs):
        data = self._data
        for k, v in kwargs.items():
            if k not in self.STANDARD_DATA_FORMAT:
                raise ValueError(f'Key entered is not valid:{k}')
            else:
                if v not in [None, True, False] and type(v) != int:
                    # encrypting value before writing to file
                    data[k] = self.encrypt(v)
                else:
                    # bool, null or ints are not encrypted
                    data[k] = v

        with open(self.file_path, 'w') as d:
            json.dump(data, d)

    def read_value(self, key):
        if key not in self.STANDARD_DATA_FORMAT:
            raise ValueError(f'Key entered is not valid:{key}')
        try:
            return self.decrypt(self._data[key.upper()])
        except AttributeError:
            return self._data[key.upper()]


# TESTING
if __name__ == '__main__':
    d = DataStore('C:\\Users\\Gavin Shaughnessy\\Desktop\\test.json', 'password')
