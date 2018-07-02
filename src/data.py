import os
import hashlib
import base64
import json

import cryptography.fernet as fernet

from . import config
from .exceptions.data_exceptions import *


class Crypto:

    def __init__(self, password):
        self._fernet = fernet.Fernet(self.key_from_password(password))
        # delete password variable
        del password  # TODO: figure out if this does anything

    @staticmethod
    def key_from_password(password, iterations=100_000):
        """ Returns a key to be used with fernet encryption"""
        b_password = password.encode('utf-8')
        b_key = hashlib.pbkdf2_hmac('sha256', b_password, b'', iterations)
        return base64.urlsafe_b64encode(b_key)

    def encrypt(self, string_):
        token = self._fernet.encrypt(string_.encode('utf-8'))
        return token.decode('utf-8')

    def decrypt(self, token):
        string_ = self._fernet.decrypt(token.encode('utf-8'))
        return string_.decode('utf-8')


# TODO: check if this class needs to actually check for existence of file
class DataStore(Crypto):

    def __init__(self, file_path, password):
        super().__init__(password)
        self.file_path = file_path

        if not os.path.exists(self.file_path):
            raise ValueError(f'{self.file_path} does not exist!')

        # new file handling
        with open(self.file_path, 'r') as d:
            if d.read() == '':
                with open(self.file_path, 'w') as dw:
                    dw.write(self.encrypt(self.json_blank_template()))

        if not self.check_password():
            raise IncorrectPasswordError('Entered password is incorrect')

    @property
    def _data(self):
        with open(self.file_path, 'r') as d:
            return json.loads(self.decrypt(d.read()))

    def _write_to_file(self, data):
        # if data is invalid for json.dumps it will raise exception here before file is overwritten
        json.dumps(data)
        with open(self.file_path, 'w') as d:
            d.write(self.encrypt(json.dumps(data)))

    @staticmethod
    def json_blank_template():
        return json.dumps(config.STANDARD_DATA_FORMAT)

    def write_value(self, allow_new_key=False, **kwargs):
        data = self._data
        for k, v in kwargs.items():

            if k not in data and allow_new_key is False:
                raise ValueError(f'Entered key ({k}) is not valid!')

            else:
                if not isinstance(v, type(config.STANDARD_DATA_FORMAT[k])):
                    raise ValueError(f'Value ({v}) is wrong type. It must be a: '
                                     f'{type(config.STANDARD_DATA_FORMAT[k])}')

                else:
                    if k in config.SENSITIVE_DATA:
                        # if key is in sensitive data list, it will be encrypted twice
                        # to limit its exposure in ram, unencrypted
                        data[k] = self.encrypt(v)

                    else:
                        data[k] = v

            self._write_to_file(data)

    def get_value(self, key):
        if key in config.SENSITIVE_DATA:
            return self.decrypt(self._data[key.upper()])

        else:
            return self._data[key.upper()]

    def check_password(self):
        try:
            # tries to decrypt data
            _ = self._data
            return True

        except fernet.InvalidToken:
            return False
