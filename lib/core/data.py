import os
import hashlib
import base64
import json

import cryptography.fernet as fernet

from . import utils
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

    def __init__(self, file_path, password, data_format=None, sensitive_keys=None):
        """
        :param file_path: path to data file
        :param password: password to encrypt data with
        :param data_format: a dictionary of allowed keys and allowed value types
        :param sensitive_keys: a list of data_format keys that should have their values double encrypted
        """
        super().__init__(password)
        self.file_path = file_path

        self.data_format = data_format if data_format is not None else {}

        # json serialised data_format to be dumped to new file
        self.json_blank_template = json.dumps(self.data_format)

        # sensitive keys will have their values encrypted twice, so when the file is read
        # and stored in memory, their values will still be encrypted
        self.sensitive_keys = sensitive_keys if sensitive_keys is not None else []

        if not os.path.exists(self.file_path):
            raise ValueError(f'{self.file_path} does not exist!')

        with open(self.file_path, 'r') as d:
            # new file handling
            if d.read() == '':
                with open(self.file_path, 'w') as dw:
                    dw.write(self.encrypt(self.json_blank_template))
            d.seek(0)

            # input checking
            try:
                if not self._check_password():
                    raise IncorrectPasswordError('Entered password is incorrect')

                json.loads(self.decrypt(d.read()))

            except json.decoder.JSONDecodeError:
                d.seek(0)
                raise InvalidFileFormat(f'Invalid JSON: {self.decrypt(d.read())}')

        # data will be stored in memory and accessed from there after first read
        # but data will constantly be written to file as it updates
        self._data = self._read_file()

        # Storing password hash for password validation independent of
        # this class i.e Wallet class for sensitive information
        if not self.get_value('PASSWORD_HASH'):
            self.write_value(PASSWORD_HASH=hashlib.sha256(password.encode('utf-8')).hexdigest())

    def change_password(self, new_password):
        # make new fernet key from password
        self._fernet = fernet.Fernet(self.key_from_password(new_password))
        # store new password hash
        self._data['PASSWORD_HASH'] = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
        # write data to file (will encrypt data using new fernet key)
        self._write_to_file(self._data)

    def _check_password(self):
        try:
            # tries to decrypt data
            _ = self._read_file()
            return True

        except fernet.InvalidToken:
            return False

    def _read_file(self):
        with open(self.file_path, 'r') as d:
            data = d.read()
            return json.loads(self.decrypt(data))

    def _write_to_file(self, data):
        # if data is invalid for json.dumps it will raise exception here before file is overwritten
        json.dumps(data)
        # update data in memory
        self._data = data

        utils.atomic_file_write(data=self.encrypt(json.dumps(data)),
                                file_path=self.file_path)

    def write_value(self, **kwargs):
        data = self._data
        for k, v in kwargs.items():

            if k not in self.data_format:
                raise ValueError(f'Entered key ({k}) is not valid!')

            else:
                if not isinstance(v, type(self.data_format[k])):
                    raise ValueError(f'Value ({v}) is wrong type. It must be a: '
                                     f'{type(self.data_format[k])}')

                else:
                    # if key is in sensitive data list, it will be encrypted twice
                    # to limit its exposure in ram, unencrypted
                    if k in self.sensitive_keys:
                        # if value is a dict, encrypt all values
                        if isinstance(v, dict):
                            data[k] = {x: self.encrypt(y) for x, y in v.items()}
                        else:
                            data[k] = self.encrypt(v)

                    else:
                        data[k] = v

        self._write_to_file(data)

    def get_value(self, key):
        if key.upper() in self.sensitive_keys:
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
        try:
            return hashlib.sha256(password.encode('utf-8')).hexdigest() \
                   == self.get_value(key='PASSWORD_HASH')
        except AttributeError:
            return False
