import os
import hashlib
import binascii
import string

import bitstring
from bip32utils.BIP32Key import BIP32Key, BIP32_HARDEN


from . import btc_verify, config
from .exceptions.bip32_exceptions import *


WORDLIST = 'wordlist.txt'
PBKDF2_HMAC_ITERATIONS = 2048  # used when converting mnemonic to seed


class Bip32:
    """ Implementation of the BIP32 Deterministic Wallet standard"""

    @classmethod
    def from_mnemonic(cls, mnemonic, passphrase='', path=config.BIP32_PATHS['bip49path'],
                      segwit=True, gap_limit=20, testnet=False):
        """ Generates a bip32 class from a mnemonic """

        if not cls.check_mnemonic(mnemonic):
            raise InvalidMnemonic(f'{mnemonic} is not a valid mnemonic')

        seed = hashlib.pbkdf2_hmac('sha512', mnemonic.encode('utf-8'),
                                   ('mnemonic' + passphrase).encode('utf-8'),
                                   PBKDF2_HMAC_ITERATIONS)

        return cls(BIP32Key.fromEntropy(seed, testnet=testnet).ExtendedKey(),
                   path, segwit, mnemonic, gap_limit)

    def __init__(self, key, path=config.BIP32_PATHS['bip49path'], segwit=True,
                 mnemonic=None, gap_limit=20):

        if not self.check_path(path):
            raise InvalidPath(f'{path} is not a valid path')

        if gap_limit <= 0:
            raise ValueError('Gap limit must be a positive int')

        self.is_private = False if key[1:4] == 'pub' else True
        self.is_segwit = segwit
        self.bip32 = BIP32Key.fromExtendedKey(key)
        self.path = path

        if self.is_private:
            self.master_private_key = self.bip32.ExtendedKey()
        self.master_public_key = self.bip32.ExtendedKey(private=False)
        self.account_public_key = self._get_account_ck().ExtendedKey(private=False)

        self.mnemonic = mnemonic

        self.gap_limit = gap_limit

        # to generate a testnet class from an extended key, the key must be
        # in the standard testnet format
        self.is_testnet = self.bip32.testnet

    @staticmethod
    def gen_mnemonic(force_use_word_list=False, length=12):
        """ Returns a new mnemonic"""
        if length not in [12, 15, 18, 21, 24]:
            raise ValueError('Mnemonic must be either 12, 15, 18, 21 or 24 words long')

        # length of mnemonic vs initial entropy length in bytes
        len_v_byte_size = {
            12: 16,
            15: 20,
            18: 24,
            21: 28,
            24: 32
        }

        # if force_use_word list is true, it skips checking validity of the file
        # (to be used with a custom word list)
        if not force_use_word_list:
            # Checking integrity of word list file
            with open(WORDLIST, 'rb') as w:
                checksum = b'Q\xca"d\xf5\xb3\xadS*Mm\xae\x17^\x17P'
                if checksum != hashlib.md5(w.read()).digest():
                    raise Exception('ERROR: Wordlist is not BIP39 valid '
                                    '(INVALID MD5 CHECKSUM)')

        # length of initial entropy in bytes
        ent_len = len_v_byte_size[length]
        ent = bitstring.BitArray(bytes=os.urandom(ent_len))

        # gets the checksum of the original ENT
        cs = bitstring.BitArray(bytes=hashlib.sha256(ent.bytes).digest()).bin[:len(ent.bin) // 32]

        ent_cs_bits = ent.bin + cs

        # split bits into groups of 11
        split_bits = [ent_cs_bits[i:i + 11] for i in range(0, len(ent_cs_bits), 11)]

        word_indexes = [int(b, 2) for b in split_bits]

        with open(WORDLIST, 'r') as w:
            word_list = w.read().split()
            mnemonic = []
            for i in word_indexes:
                mnemonic.append(word_list[i])

        # Returns the mnemonic in string format
        return ' '.join(mnemonic)

    # Adapted from <https://tinyurl.com/ycxfjmd6>
    @staticmethod
    def check_mnemonic(mnemonic):
        """ Returns True if mnemonic is valid and vice-versa"""
        with open(WORDLIST, 'r') as w:
            wordlist = w.read().split()
        mnemonic = mnemonic.split(' ')

        if len(mnemonic) not in [12, 15, 18, 21, 24]:
            return False

        try:
            idx = map(lambda x: bin(wordlist.index(x))[2:].zfill(11), mnemonic)
            b = ''.join(idx)
        except Exception:
            return False

        len_b = len(b)
        d = b[:len_b // 33 * 32]
        h = b[-len_b // 33:]
        nd = binascii.unhexlify(hex(int(d, 2))[2:].rstrip('L').zfill(len_b // 33 * 8))
        nh = bin(int(hashlib.sha256(nd).hexdigest(), 16))[2:].zfill(256)[:len_b // 33]

        return h == nh

    @staticmethod
    def check_path(path):
        """ returns True if path is in a valid format and vice-versa"""

        valid_chars = string.digits + '/' + "'"
        valid_index_chars = string.digits + "'"
        split_path = path.split('/')

        if not all([True for c in path if c in valid_chars]):
            return False

        for idx in split_path:

            if idx == '':
                return False

            for e, c in enumerate(idx):

                if c not in valid_index_chars:
                    return False

                if c == "'" and e != len(idx) - 1:
                    return False

        return True

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

        if self.is_segwit:
            for i in range(self.gap_limit):
                receiving.append(ck.ChildKey(0).ChildKey(i).P2WPKHoP2SHAddress())
            for i in range(self.gap_limit):
                change.append(ck.ChildKey(1).ChildKey(i).P2WPKHoP2SHAddress())
        else:
            for i in range(self.gap_limit):
                receiving.append(ck.ChildKey(0).ChildKey(i).Address())
            for i in range(self.gap_limit):
                change.append(ck.ChildKey(1).ChildKey(i).Address())

        # Sanity checks
        if btc_verify.check_bc(receiving + change):
            return receiving, change
        else:
            raise Exception('Unexpected error occurred in address generation')

    def wif_keys(self):
        """ Returns a tuple of receiving and change WIF keys up to the limit specified """
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

    # def raw_private_keys(self):
    #     """ Returns hex bitcoin private keys"""
    #     if not self.is_private:
    #         raise WatchOnlyWallet('Can\'t derive private key from watch-only wallet')
    #
    #     receiving = []
    #     change = []
    #     ck = self._get_account_ck()
    #
    #     for i in range(self.gap_limit):
    #         receiving.append(ck.ChildKey(0).ChildKey(i).PrivateKey().hex())
    #     for i in range(self.gap_limit):
    #         change.append(ck.ChildKey(1).ChildKey(i).PrivateKey().hex())
    #
    #     return receiving, change

    # TODO: FIX TERRIBLE PERFORMANCE HERE
    def address_wifkey_pairs(self):
        """ Returns a list of tuples with addresses mapped to their WIF keys """
        if not self.is_private:
            raise WatchOnlyWallet('Can\'t derive private key from watch-only wallet')

        # both receiving and change addresses/wif keys in single lists
        addresses = self.addresses()[0] + self.addresses()[1]
        wif_keys = self.wif_keys()[0] + self.wif_keys()[1]

        return list(zip(addresses, wif_keys))

    def set_gap_limit(self, num):
        if not isinstance(num, int):
            raise ValueError('Gap limit must be an int')
        elif num <= 0:
            raise ValueError('Gap limit must be at least 1')
        else:
            self.gap_limit = num
