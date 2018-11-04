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

import os
import hashlib
import base64
import json
import copy
import threading

import cryptography.fernet as fernet

from ..core import utils
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
        str_bytes = self._fernet.decrypt(string_token.encode('utf-8'))
        return str_bytes.decode('utf-8')


class DataStore:

    # dict of file paths and instances of DataStore.
    _instances = {}

    # if the same file_path is used, the same object will be returned.
    # any file should only have one DataStore object associated with them
    # as it could get messy with multiple objects writing to the same file
    # (especially when dealing with threads).
    def __new__(cls, file_path, *args, **kwargs):
        if file_path in cls._instances:
            return cls._instances[file_path]
        else:
            new_cls = super().__new__(cls)
            cls._instances[file_path] = new_cls

            return new_cls

    @classmethod
    def new_data_store(cls, file_path, password, data_format, sensitive_keys=None):
        """ alternative constructor for DataStore that creates and formats new file """

        # format for file, setting data format keys to their instantiated types
        json_blank_template = json.dumps({k: v() for k, v in data_format.items()})
        crypto = Crypto(password)

        with open(file_path, 'w') as f:
            json.dump(crypto.encrypt(json_blank_template), f)

        return cls(file_path, password, data_format, sensitive_keys)

    def __init__(self, file_path, password, data_format, sensitive_keys=None):
        """
        :param file_path: path to data file
        :param password: password to encrypt data with
        :param data_format: a dictionary of allowed keys and allowed value types (None will be set
        to new instance of allowed type when writing)
        :param sensitive_keys: a list of data_format keys that should have their values encrypted
        on top of regular file encryption
        """
        self.file_path = file_path
        self.data_format = data_format
        self.sensitive_keys = sensitive_keys if sensitive_keys is not None else []
        self.crypto = Crypto(password)

        self.write_lock = threading.Lock()

        if not data_format:
            raise ValueError('Data format must be specified')

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f'{self.file_path} does not exist!')

        if not self._check_password():
            raise IncorrectPasswordError('Entered password is incorrect')

        if not all(self.data_format[k] in (str, dict) for k in self.sensitive_keys):
            raise ValueError('Sensitive key values must be either a string or a dict')

        # data will be stored in memory and accessed from there after first read
        # but data will constantly be written to file as it updates
        self._internal_data = self._read_file()

        # if there are any new keys in the data format that aren't present in the file, create them
        self._write_new_keys()

        # TODO: make a password a requirement for decryption of sensitive keys,
        # TODO: not this simple hash verification
        # Storing password hash for password validation independent of
        # this class i.e Wallet class for sensitive information
        if not self.get_value('PASSWORD_HASH'):
            # use internal write values as thread not started yet
            self.write_values(PASSWORD_HASH=hashlib.sha256(password.encode('utf-8')).hexdigest())

    @property
    def _data(self):
        """ returns copy of data
        self._internel_data is only accessed directly by self._write_data_to_file.
        This is to ensure the internal object state is consistent, especially
        when threads are being used to modify data.
        """
        return copy.deepcopy(self._internal_data)

    def _write_new_keys(self):
        """ if there are any keys present in self.data_format that
        aren't in file, the file will be updated with the new keys.
        (for backwards compatibility with old DataStore files)
        """
        data = {}
        for k in self.data_format:
            if k not in self._data:
                data[k] = self.data_format[k]()

        self._write_data_to_file(data)

    def _check_password(self):
        try:
            # tries to decrypt data
            _ = self._read_file()
            return True

        except fernet.InvalidToken:
            return False

    def _read_file(self):
        with open(self.file_path, 'r') as d:
            data = self.crypto.decrypt(d.read())
            return json.loads(data)

    def _write_data_to_file(self, data):
        """ data should be a dict of self.data_format key/values to be updated in the file """
        # sanity checks, real validation of data should have been done by callers
        assert all(k in self.data_format and isinstance(v, self.data_format[k]) for k, v in data.items())

        # if data is invalid for json.dumps it will raise exception here before file is overwritten
        json.dumps(data)

        with self.write_lock:
            # update data in memory
            self._internal_data.update(data)

            utils.atomic_file_write(data=self.crypto.encrypt(json.dumps(self._internal_data)),
                                    file_path=self.file_path)

    def _encrypt_dict_string_values(self, dict_):
        """ goes through a dict and encrypts all string values, and all string values in nested dicts """

        # work with copy of dict that will overwrite dict_, to prevent a half encrypted dict left
        # after a possible max recursion depth exception
        # (need deepcopy to copy dicts and not references to same dict)
        copy_dict = copy.deepcopy(dict_)

        for k, v in copy_dict.items():
            if isinstance(v, str):
                copy_dict.update({k: self.crypto.encrypt(v)})

            elif isinstance(v, dict):
                self._encrypt_dict_string_values(v)

        dict_.update(copy_dict)

    def write_values(self, **kwargs):
        data = {}
        for k, v in kwargs.items():

            # if v is None, set it to a new instance if its proper type
            if v is None:
                v = self.data_format[k]()

            if k not in self.data_format:
                raise ValueError(f'Entered key ({k}) is not valid!')

            else:
                if not isinstance(v, self.data_format[k]):
                    raise ValueError(f'Value ({v}) is wrong type. It must be a: '
                                     f'{self.data_format[k]}')

                else:
                    # if key is in sensitive data list, it will be encrypted twice
                    # to limit its exposure in ram, unencrypted
                    if k in self.sensitive_keys:
                        if isinstance(v, dict):
                            self._encrypt_dict_string_values(v)
                            data.update({k: v})

                        elif isinstance(v, str):
                            data[k] = self.crypto.encrypt(v)
                        else:
                            raise ValueError(f'Invalid sensitive data type: "{type(v)}"')

                    else:
                        data[k] = v

        self._write_data_to_file(data)

    def get_value(self, key):
        value = self._data[key.upper()]

        # if value is a dict, it is presumed that the values
        # in the dict will be decrypted when needed, so only strings
        # are decrypted. (string and dicts are only types allowed in sensitive data)
        if key.upper() in self.sensitive_keys and isinstance(value, str):
            return self.crypto.decrypt(value)

        else:
            # return deepcopy for other types than immutable string (dicts mainly)
            return copy.deepcopy(value)

    def change_password(self, new_password):
        data = {}
        # make new fernet key from password
        self.crypto._fernet = fernet.Fernet(self.crypto.key_from_password(new_password))
        # store new password hash
        data['PASSWORD_HASH'] = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
        # write data to file (will encrypt data using new fernet key)
        self._write_data_to_file(data)

    # for use outside this class, where the password isn't actually used
    # to decrypt the file, but still needs to be verified for security
    def validate_password(self, password):
        try:
            return hashlib.sha256(password.encode('utf-8')).hexdigest() \
                   == self.get_value(key='PASSWORD_HASH')
        except AttributeError:
            return False
