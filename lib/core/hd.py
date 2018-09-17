import os
import hashlib
import binascii
import string
import multiprocessing
from operator import itemgetter
from functools import lru_cache
from contextlib import suppress

import bitstring
import base58
from .bip32utils_updated.BIP32Key import BIP32Key, BIP32_HARDEN

from .utils import IterableQueue
from ..exceptions.hd_exceptions import *


class HDWallet:
    """ implementation of the hierarchical deterministic wallet, implementing the BIP39 standard """

    @classmethod
    def from_mnemonic(cls, mnemonic, path, passphrase='',
                      segwit=True, gap_limit=20, testnet=False, multi_processing=True):
        """ Generates a HDWallet class from a mnemonic """

        pbkdf2_hmac_iterations = 2048

        if not cls.check_mnemonic(mnemonic):
            raise InvalidMnemonic(f'{mnemonic} is not a valid mnemonic')

        seed = hashlib.pbkdf2_hmac('sha512', mnemonic.encode('utf-8'),
                                   ('mnemonic' + passphrase).encode('utf-8'),
                                   pbkdf2_hmac_iterations)

        return cls(BIP32Key.fromEntropy(seed, testnet=testnet).ExtendedKey(),
                   path, segwit, mnemonic, gap_limit, multi_processing)

    def __init__(self, key, path, segwit=True, mnemonic=None, gap_limit=20, multi_processing=True):

        if not self.check_path(path):
            raise InvalidPath(f'{path} is not a valid path')

        if gap_limit <= 0:
            raise ValueError('Gap limit must be a positive int')

        if not self.check_xkey(key):
            raise ValueError(f'Invalid Extended Key: ({key})')

        self.is_private = False if key[1:4] == 'pub' else True

        # apostrophes in a path denote a hardened key, which can only be derived from a private key
        if not self.is_private and "'" in path:
            raise PublicHDWalletObjectError('Cannot derive a hardened child key from a public key')

        self.is_segwit = segwit
        self.bip32 = BIP32Key.fromExtendedKey(key, public=not self.is_private)
        self.path = path

        self.master_private_key = self.bip32.ExtendedKey() if self.is_private else None
        self.master_public_key = self.bip32.ExtendedKey(private=False)
        self.account_public_key = self._account_ck.ExtendedKey(private=False)

        self.mnemonic = mnemonic

        self.gap_limit = gap_limit

        # to generate a testnet class from an extended key, the key must be
        # in the standard testnet format
        self.is_testnet = self.bip32.testnet

        self.multi_processed = multi_processing

        # multiprocessing currently causes issues when deriving keys from public keys.
        # But due to the fact that only addresses can be generated from a public key,
        # the performance hit is tolerable. If a watch only wallet is ever implemented
        # using this class, the slight performance hit at creation is acceptable
        if not self.is_private:
            self.multi_processed = False

        self._external_chain_ck = self._account_ck.ChildKey(0)
        self._internal_chain_ck = self._account_ck.ChildKey(1)

        # for multiprocessing gen of addresses/wif_keys
        _manager = multiprocessing.Manager()
        self._address_queue = _manager.Queue()
        self._wif_key_queue = _manager.Queue()

    @staticmethod
    def wordlist():
        wl = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'wordlist.txt')
        with open(wl, 'r') as word_file:
            return word_file.read().split()

    @classmethod
    def gen_mnemonic(cls, length=12):
        """ Returns a new mnemonic"""
        wordlist = cls.wordlist()

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

        # Checking integrity of word list file
        wl_hash = '2a80fc2c95f3a4b0a5769764df251820'
        if wl_hash != hashlib.md5(''.join(wordlist).encode()).hexdigest():
            raise Exception('ERROR: Wordlist is not BIP39 valid '
                            '(INVALID MD5 HASH)')

        # length of initial entropy in bytes
        ent_len = len_v_byte_size[length]
        ent = bitstring.BitArray(bytes=os.urandom(ent_len))

        # gets the checksum of the original ENT
        cs = bitstring.BitArray(bytes=hashlib.sha256(ent.bytes).digest()).bin[:len(ent.bin) // 32]

        ent_cs_bits = ent.bin + cs

        # split bits into groups of 11
        split_bits = [ent_cs_bits[i:i + 11] for i in range(0, len(ent_cs_bits), 11)]

        word_indexes = [int(b, 2) for b in split_bits]

        mnemonic = []
        for i in word_indexes:
            mnemonic.append(wordlist[i])

        # Returns the mnemonic in string format
        return ' '.join(mnemonic)

    # Adapted from <https://tinyurl.com/ycxfjmd6>
    @classmethod
    def check_mnemonic(cls, mnemonic):
        """ Returns True if mnemonic is valid and vice-versa"""
        wordlist = cls.wordlist()

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
    def check_xkey(xkey, allow_testnet=True):
        xkey_version_bytes = ('0488B21E', '0488ADE4')

        if allow_testnet:
            xkey_version_bytes += ('043587CF', '04358394')

        with suppress(ValueError, TypeError):
            if base58.b58decode_check(xkey)[:4].hex().upper() in xkey_version_bytes:
                return True

        return False

    @staticmethod
    def check_path(path):
        """ returns True if path is in a valid format and vice-versa"""

        valid_chars = string.digits + '/' + "'"
        valid_index_chars = string.digits + "'"
        split_path = path.split('/')

        if split_path[0].lower() == 'm':
            del split_path[0]

        if not all([c in valid_chars for c in path]):
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

    @property
    @lru_cache(maxsize=None)
    def _account_ck(self):
        """returns an 'account' child key. i.e the last derivation of the path"""
        # First get a child key (ck) to derive from further in a loop
        split_path = self.path.split('/')

        if split_path[0].lower() == 'm' and len(split_path) == 1:
            return self.bip32
        elif split_path[0].lower() == 'm':
            # remove redundant m if it is part of bigger path
            del split_path[0]

        if split_path[0][-1] == "'":
            ck = self.bip32.ChildKey(int(split_path[0][:-1]) + BIP32_HARDEN)
        else:
            ck = self.bip32.ChildKey(int(split_path[0]))

        # Loop over the rest of the split path to derive other keys
        for i in split_path[1:]:
            if i[-1] == "'":
                ck = ck.ChildKey(int(i[:-1]) + BIP32_HARDEN)
            else:
                ck = ck.ChildKey(int(i))

        return ck

    def delete_sensitive_data(self):
        self.bip32.SetPublic()
        del self.bip32

    @lru_cache(maxsize=None)
    def _gen_addresses(self, idx):
        """ used with multiprocessing """
        if self.is_segwit:
            r_address = self._external_chain_ck.ChildKey(idx).P2WPKHoP2SHAddress()
            c_address = self._internal_chain_ck.ChildKey(idx).P2WPKHoP2SHAddress()
        else:
            r_address = self._external_chain_ck.ChildKey(idx).Address()
            c_address = self._internal_chain_ck.ChildKey(idx).Address()

        self._address_queue.put((idx, r_address, c_address))

    def _multi_processed_addresses(self):
        """ Returns a tuple of receiving and change addresses up to the limit specified"""
        receiving = []
        change = []

        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        pool.map(self._gen_addresses, range(self.gap_limit))

        sorted_addresses = sorted(IterableQueue(self._address_queue), key=itemgetter(0))
        for a in sorted_addresses:
            receiving.append(a[1])
            change.append(a[2])

        return receiving, change

    def _non_multi_processed_addresses(self):
        """ deriving from a public key does not currently work with multiprocessing"""
        receiving = []
        change = []

        for i in range(self.gap_limit):
            if self.is_segwit:
                receiving.append(self._external_chain_ck.ChildKey(i).P2WPKHoP2SHAddress())
                change.append(self._internal_chain_ck.ChildKey(i).P2WPKHoP2SHAddress())
            else:
                receiving.append(self._external_chain_ck.ChildKey(i).Address())
                change.append(self._internal_chain_ck.ChildKey(i).Address())

        return receiving, change

    @lru_cache(maxsize=None)
    def _gen_wif_keys(self, idx):
        """ used with multiprocessing """
        r_keys = self._external_chain_ck.ChildKey(idx).WalletImportFormat()
        c_keys = self._internal_chain_ck.ChildKey(idx).WalletImportFormat()

        self._wif_key_queue.put((idx, r_keys, c_keys))

    def _multi_processed_wif_keys(self):
        """ Returns a tuple of receiving and change WIF keys up to the limit specified """
        receiving = []
        change = []

        pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())
        pool.map(self._gen_wif_keys, range(self.gap_limit))

        sorted_keys = sorted(IterableQueue(self._wif_key_queue), key=itemgetter(0))
        for w in sorted_keys:
            receiving.append(w[1])
            change.append(w[2])

        return receiving, change

    def _non_multi_processed_wif_keys(self):
        receiving = []
        change = []

        for i in range(self.gap_limit):
            receiving.append(self._external_chain_ck.ChildKey(i).WalletImportFormat())
            change.append(self._internal_chain_ck.ChildKey(i).WalletImportFormat())

        return receiving, change

    def addresses(self):
        if self.multi_processed:
            return self._multi_processed_addresses()
        else:
            return self._non_multi_processed_addresses()

    def wif_keys(self):
        if not self.is_private:
            return None

        if self.multi_processed:
            return self._multi_processed_wif_keys()
        else:
            return self._non_multi_processed_wif_keys()

    def address_wifkey_pairs(self):
        """ Returns a list of tuples with addresses mapped to their WIF keys """
        if not self.is_private:
            return None

        addresses = self.addresses()
        wif_keys = self.wif_keys()

        return list(zip(addresses[0] + addresses[1], wif_keys[0] + wif_keys[1]))

    def set_gap_limit(self, num):
        if not isinstance(num, int):
            raise ValueError('Gap limit must be an int')
        elif num <= 0:
            raise ValueError('Gap limit must be at least 1')
        else:
            self.gap_limit = num
