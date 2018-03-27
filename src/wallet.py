import os
import hashlib
import base64
import json

import cryptography.fernet as fernet

from src.bip32 import Bip32
import src.config as CONFIG


class Crypto:

    def __init__(self, password):
        self.fernet = fernet.Fernet(self.key_from_password(password))

    @staticmethod
    def key_from_password(password, iterations=100_000):
        """ Returns a key to be used with fernet encryption"""
        b_password = password.encode('utf-8')
        b_key = hashlib.pbkdf2_hmac('sha256', b_password, b'', iterations)
        return base64.urlsafe_b64encode(b_key)

    def encrypt(self, string):
        return self.fernet.encrypt(string.encode('utf-8')).decode('utf-8')

    def decrypt(self, string):
        return self.fernet.decrypt(string.encode('utf-8')).decode('utf-8')


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

    def __init__(self, file_path, password):
        super().__init__(password)
        self.file = open(file_path, 'r+')

    @property
    def _data(self):
        return json.load(self.file)

    def write_value(self, **kwargs):
        data = self._data
        self.file.flush()
        for k, v in kwargs.items():
            if k not in self.STANDARD_DATA_FORMAT:
                raise ValueError('Invalid keys entered')
            else:
                data[k] = v
        json.dump(data, self.file)


    def _write_blank_template(self):
        json.dump(self.STANDARD_DATA_FORMAT, self.file)



d = DataStore('C:\\Users\\Gavin Shaughnessy\\Desktop\\test.json', 'password')
#d._write_blank_template()
d.write_value(XPRIV='123cret', MNEMONIC='ewwdw')

