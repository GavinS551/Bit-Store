import os
import hashlib

import bitstring

from src.bip32utils.BIP32Key import BIP32Key, BIP32_HARDEN
from src import btc_verify, config


class WatchOnlyWallet(Exception):
    """ Raised when trying to derive private keys from a watch-only wallet """
    pass


class Bip32:
    """ Implementation of the BIP32 Deterministic Wallet standard"""

    @classmethod
    def from_mnemonic(cls, mnemonic, passphrase='', path=config.BIP32_PATHS['bip49path'],
                      force_segwit=False, testnet=False):
        """ Generates a bip32 class from a mnemonic """
        seed = hashlib.pbkdf2_hmac('sha512', mnemonic.encode('utf-8'),
                                   ('mnemonic' + passphrase).encode('utf-8'), 2048)

        return cls(BIP32Key.fromEntropy(seed, testnet=testnet).ExtendedKey(),
                   path, force_segwit, mnemonic)

    def __init__(self, key, path=config.BIP32_PATHS['bip49path'], force_segwit=False, mnemonic=None):
        self.is_private = False if key[1:4] == 'pub' else True
        # path must use "purpose" of 49 else legacy addresses will be generated
        self.segwit = True if path[:2] == '49' or force_segwit else False
        self.bip32 = BIP32Key.fromExtendedKey(key)
        self.path = path

        if self.is_private:
            self.master_private_key = self.bip32.ExtendedKey()
        self.master_public_key = self.bip32.ExtendedKey(private=False)
        self.account_public_key = self._get_account_ck().ExtendedKey(private=False)

        self.mnemonic = mnemonic

        # Gap limit for address gen
        self.gap_limit = 20

        self.is_testnet = self.bip32.testnet

    @staticmethod
    def gen_mnemonic(force_use_word_list=False):
        """ Returns a new 16 word mnemonic"""

        # if force_use_word list is true, it skips checking validity of the file
        # to be used with a custom word list
        if not force_use_word_list:
            # Checking integrity of word list file
            with open('wordlist.txt', 'rb') as w:
                checksum = b'Q\xca"d\xf5\xb3\xadS*Mm\xae\x17^\x17P'
                if checksum != hashlib.md5(w.read()).digest():
                    raise Exception('ERROR: Wordlist is not BIP39 valid '
                                    '(INVALID MD5 CHECKSUM)')

        ent_len = 16  # length of initial entropy in bytes
        cs_slice_index = 1  # max index of the checksum slice

        ent = os.urandom(ent_len)
        # gets the checksum of the original ENT
        cs = hashlib.sha256(ent).hexdigest()[0:cs_slice_index]
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

    def _get_account_ck(self):
        """returns an 'account' child key. i.e the last derivation of the path"""
        
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

    def addresses(self):
        """ Returns a tuple of receiving and change addresses up to the limit specified"""
        receiving = []
        change = []
        ck = self._get_account_ck()

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

        # Check to make sure that addresses are 100% valid, because better safe than sorry
        for a in receiving + change:
            if btc_verify.check_bc(a):
                return receiving, change
            else:
                raise Exception('Unexpected error occurred in address'
                                ' generation: INVALID ADDRESS GENERATED')

    def wif_keys(self):
        """ Returns a tuple of receiving and change WIF keys up to the limit specified"""
        if not self.is_private:
            raise WatchOnlyWallet('Can\'t derive private key from watch-only wallet')

        receiving = []
        change = []
        ck = self._get_account_ck()

        for i in range(self.gap_limit):
            receiving.append(ck.ChildKey(0).ChildKey(i).WalletImportFormat())
        for i in range(self.gap_limit):
            change.append(ck.ChildKey(1).ChildKey(i).WalletImportFormat())

        return receiving, change

    def set_gap_limit(self, num):
        if num != type(int):
            raise ValueError('Gap limit must be an int')
        elif num <= 0:
            raise ValueError('Gap limit must be atleast 1')
        else:
            self.gap_limit = num


if __name__ == '__main__':
    b = Bip32.from_mnemonic('tiny useless make elegant meadow lobster clown record buzz goddess rookie purity')
    print(b.master_private_key)
    print(b.master_public_key)
    print(b.account_public_key)