import os
import hashlib
import base64
import json

import cryptography.fernet as fernet

import src.config as config


class Crypto:

    def __init__(self, password):
        self._fernet = fernet.Fernet(self.key_from_password(password))
        del(password)  # delete password variable

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

    class IncorrectPassword(Exception):
        pass

    def __init__(self, file_path, password):
        super().__init__(password)
        self.file_path = file_path

        if not os.path.exists(self.file_path):
            raise ValueError(f'{self.file_path} does not exist!')

        # new file handling
        with open(self.file_path, 'r') as d:
            if d.read() == '':
                d.write(self.encrypt(self.json_blank_template()))

        self.check_password()  # password validity handling

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
                    raise ValueError(f'Value is wrong type. It must be a: '
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
        return self._data[key.upper()]

    def check_password(self):
        try:
            # tries to decrypt data
            _ = self._data
        except fernet.InvalidToken:
            raise self.IncorrectPassword('Entered password is incorrect')


if __name__ == '__main__':

    ds = DataStore(r'C:\Users\Gavin Shaughnessy\Desktop\data.json', 'hello')
