import os
import hashlib
import base64

import cryptography.fernet as fernet

from src.bip32 import Bip32
import src.config as CONFIG


class Wallet:

    @classmethod
    def new_wallet(cls, name):
        dir_ = os.path.join(CONFIG.DATA_DIR, name)
        # If data directory doesn't exist it will create it
        if not os.path.isdir(CONFIG.DATA_DIR):
            os.mkdir(CONFIG.DATA_DIR_NAME)

        if os.path.isdir(dir_):
            raise Exception('Wallet already exists!')
        else:
            os.mkdir(dir_)

        with open(os.path.join(dir_, 'data.json'), 'w+') as d:
            d.write('{}')

        with open(os.path.join(dir_, 'prices.json'), 'w+') as p:
            p.write('{}')

        return cls(name)

    def __init__(self, name):
        self.dir = os.path.join(CONFIG.DATA_DIR, name)
        if not os.path.isdir(self.dir):
            raise Exception('Wallet file doesn\'t exist!')


class Crypto:

    def __init__(self, password):
        self.fernet = fernet.Fernet(self.key_from_password(password))

    @staticmethod
    def key_from_password(password, iterations=100_000):
        """ Returns a key to be used with fernet encryption"""
        b_password = password.encode('utf-8')
        b_key = hashlib.pbkdf2_hmac('sha256', b_password, b'', iterations)
        return base64.urlsafe_b64encode(b_key)

