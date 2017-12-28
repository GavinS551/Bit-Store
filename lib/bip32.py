import os
import hashlib

import bitstring
from lib.bip32utils.BIP32Key import BIP32Key, BIP32_HARDEN


class WatchOnlyWallet(Exception):
    """ Raised when trying to derive private keys from a watch-only wallet """
    pass


class Bip32:
    """ Implementation of the BIP32 Deterministic Wallet standard"""
    PATHS = {
        'bip49path': "49'/0'/0'",
        'bip44path': "44'/0'/0'"
    }

    @classmethod
    def from_mnemonic(cls, mnemonic, passphrase='', path=PATHS['bip49path'], force_segwit=False):
        """ Generates a bip32 class from a mnemonic """
        seed = hashlib.pbkdf2_hmac('sha512', mnemonic.encode('utf-8'),
                                   ('mnemonic' + passphrase).encode('utf-8'), 2048)

        return cls(BIP32Key.fromEntropy(seed).ExtendedKey(), path, force_segwit, mnemonic=mnemonic)

    def __init__(self, key, path=PATHS['bip49path'], force_segwit=False, mnemonic=None):
        self.is_private = False if key[1:4] == 'pub' else True
        # path must use "purpose" of 49 else legacy addresses will be generated
        self.segwit = True if path[:2] == '49' or force_segwit else False
        self.bip32 = BIP32Key.fromExtendedKey(key)
        self.path = path

        if self.is_private:
            self.master_private_key = self.bip32.PrivateKey()
        self.master_public_key = self.bip32.PublicKey()
        self.mnemonic = mnemonic

        # amount of addresses to generate
        self.gap_limit = 20

    @staticmethod
    def gen_mnemonic():
        """ Returns a new 16 word mnemonic"""
        ent = os.urandom(16)
        # gets the checksum of the original ENT
        cs = hashlib.sha256(ent).hexdigest()[0]
        ent_cs = ent.hex() + cs
        # Turns ent_cs into a bit array so it can be split into groups of 11 bits
        bits = bitstring.BitArray(hex=ent_cs)
        split_bits = [bits.bin[i:i+11] for i in range(0, len(bits.bin), 11)]
        word_indexes = [int(b, 2) for b in split_bits]

        with open('wordlist.txt', 'r') as w:
            word_list = w.read().split()
            mnemonic = []
            for i in word_indexes:
                mnemonic.append(word_list[i])

        # Returns the mnemonic in string format
        return ' '.join(mnemonic)

    def _get_base_ck(self):
        """ Returns a "base" child key; i.e external and internal chains are derived from here """
        # First get a child key (ck) to derive from further in a loop
        split_path = self.path.split('/')
        if split_path[0][-1] == "'":
            ck = self.bip32.ChildKey(int(split_path[0][:-1]) + BIP32_HARDEN)
        else:
            ck = self.bip32.ChildKey(int(split_path[0]))

        # Loop over the rest of the split path to derive other keys
        for i in split_path[1:]:
            if i[-1] == "'":
                ck = ck.ChildKey(int(i[:-1]) + BIP32_HARDEN)
            else:
                ck = ck.ChildKey(int(i[:-1]))

        return ck

    def addresses(self):  # 20 is the gap limit for discovering new addresses
        """ Returns a tuple of receiving and change addresses up to the limit specified"""
        receiving = []
        change = []
        ck = self._get_base_ck()

        if self.segwit:
            for i in range(self.gap_limit):
                receiving.append(ck.ChildKey(0).ChildKey(i).P2WPKHoP2SHAddress())
            for i in range(self.gap_limit):
                change.append(ck.ChildKey(1).ChildKey(i).P2WPKHoP2SHAddress())
        else:
            for i in range(self.gap_limit):
                receiving.append(ck.ChildKey(0).ChildKey(i).Address())
            for i in range(self.gap_limit):
                change.append(ck.ChildKey(1).ChildKey(i).Address())

        return receiving, change

    def wif_keys(self):
        """ Returns a tuple of receiving and change WIF keys up to the limit specified"""
        if not self.is_private:
            raise WatchOnlyWallet('Can\'t derive private key from watch-only wallet')

        receiving = []
        change = []
        ck = self._get_base_ck()

        for i in range(self.gap_limit):
            receiving.append(ck.ChildKey(0).ChildKey(i).WalletImportFormat())
        for i in range(self.gap_limit):
            change.append(ck.ChildKey(1).ChildKey(i).WalletImportFormat())

        return receiving, change
