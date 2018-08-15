import os
import hashlib
import base64
import json

import cryptography.fernet as fernet

from . import config
from ..exceptions.data_exceptions import *


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

    def decrypt(self, string_token):
        string = self._fernet.decrypt(string_token.encode('utf-8'))
        return string.decode('utf-8')


class DataStore(Crypto):

    def __init__(self, file_path, password):
        super().__init__(password)
        self.file_path = file_path
        self.json_blank_template = json.dumps(config.STANDARD_DATA_FORMAT)

        if not os.path.exists(self.file_path):
            raise ValueError(f'{self.file_path} does not exist!')

        # input checking
        with open(self.file_path, 'r') as d:
            # new file handling
            if d.read() == '':
                with open(self.file_path, 'w') as dw:
                    dw.write(self.encrypt(self.json_blank_template))

            # check to see if file is valid json if not blank
            else:
                try:
                    if not self._check_password():
                        raise IncorrectPasswordError('Entered password is incorrect')

                    d.seek(0)  # d.read() was already called in above if statement
                    json.loads(self.decrypt(d.read()))
                except json.decoder.JSONDecodeError:
                    raise InvalidFileFormat(f'Invalid JSON: {self.decrypt(d.read())}')

        # Storing password hash for password validation independent of
        # this class i.e Wallet class for sensitive information
        self.write_value(PASSWORD_HASH=hashlib.sha256(password.encode('utf-8')).hexdigest())

        # initialise cached data - cached for threaded compatibility, see _data property
        self._cached_data = self._data

    def _check_password(self):
        try:
            # tries to decrypt data
            _ = self._data
            return True

        except fernet.InvalidToken:
            return False

    @property
    def _data(self):
        with open(self.file_path, 'r') as d:
            data = d.read()

            # for threaded compatibility - if one thread is mid write and the
            # file is blank, cached value will be returned
            if data:
                self._cached_data = data
                return json.loads(self.decrypt(data))
            else:
                return json.loads(self.decrypt(self._cached_data))

    def _write_to_file(self, data):
        # if data is invalid for json.dumps it will raise exception here before file is overwritten
        json.dumps(data)
        with open(self.file_path, 'w') as d:
            d.write(self.encrypt(json.dumps(data)))

    def write_value(self, allow_new_key=False, **kwargs):
        data = self._data
        for k, v in kwargs.items():

            if k not in config.STANDARD_DATA_FORMAT and allow_new_key is False:
                raise ValueError(f'Entered key ({k}) is not valid!')

            else:
                if not isinstance(v, type(config.STANDARD_DATA_FORMAT[k])):
                    raise ValueError(f'Value ({v}) is wrong type. It must be a: '
                                     f'{type(config.STANDARD_DATA_FORMAT[k])}')

                else:
                    # if key is in sensitive data list, it will be encrypted twice
                    # to limit its exposure in ram, unencrypted
                    if k in config.SENSITIVE_DATA:
                        # if value is a dict, encrypt all values
                        if isinstance(v, dict):
                            data[k] = {x:self.encrypt(y) for x, y in v.items()}
                        else:
                            data[k] = self.encrypt(v)

                    else:
                        data[k] = v

            self._write_to_file(data)

    def get_value(self, key):
        if key.upper() in config.SENSITIVE_DATA:
            # if value is a dict, values wont be decrypted as that will be
            # done only when needed to sign txns (only key that is currently
            # implemented is a dict stores address/wif keys)
            if isinstance(self._data[key.upper()], dict):
                return self._data[key.upper()]

            else:
                return self.decrypt(self._data[key.upper()])

        else:
            return self._data[key.upper()]

    # for use outside this class, where the password isn't actually used
    # to decrypt the file, but still needs to be verified for security
    def validate_password(self, password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest() \
               == self.get_value(key='PASSWORD_HASH')
