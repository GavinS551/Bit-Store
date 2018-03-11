import os.path

import cryptography
from src.bip32 import Bip32


class Wallet:

    @classmethod
    def new_wallet(cls, name):



        return cls()

    def __init__(self, dir_):
        self.dir = dir_
        self.name = os.path.basename(self.dir)

