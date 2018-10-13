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
import threading
import shutil
import enum
import time
import json
import pickle
import hashlib
import binascii

import requests.exceptions

from . import blockchain, config, data, tx, price, hd, structs, utils
from ..exceptions.wallet_exceptions import *


API_REFRESH_RATE = 5
API_REFRESH_RATE_LOWER = 5

GAP_LIMIT_MIN = 20
GAP_LIMIT_MAX = 50


def get_wallet(name, password):
    """ function will return wallet of correct type (normal or watch-only) """
    watch_only = Wallet.get_metadata(name)['watch_only']

    if watch_only:
        return WatchOnlyWallet(name, password)
    else:
        return Wallet(name, password)


def is_wallet(name):
    """ checks if the directory is a valid wallet """
    full_path = lambda w: os.path.join(config.WALLET_DATA_DIR, w)
    return all(f in os.listdir(full_path(name)) for f in (config.WALLET_DATA_FILE_NAME, config.WALLET_INFO_FILE_NAME))


class _ApiDataUpdaterThread(threading.Thread):

    class ApiConnectionStatus(enum.Enum):

        good = 0
        first_attempt = 1
        error = 2

    def __init__(self, wallet_instance, refresh_rate):

        if not isinstance(wallet_instance, Wallet):
            raise TypeError('wallet_instance must be an instance of Wallet class')

        if not isinstance(refresh_rate, int):
            raise TypeError('Refresh rate must be an int')

        # due to api request limits
        if refresh_rate < API_REFRESH_RATE_LOWER:
            raise ValueError(f'Refresh rate must be at least {API_REFRESH_RATE_LOWER} seconds')

        threading.Thread.__init__(self, name='API_DATA_UPDATER')
        # event will be set outside of this class
        self.event = threading.Event()
        self.wallet_instance = wallet_instance
        self.refresh_rate = refresh_rate
        # a requests Exception, stored if the last data request failed
        # if last request was successful, store False
        self.connection_exception = None
        self.connection_status = self.ApiConnectionStatus.first_attempt

        self.connection_timestamp = None

        # blockchain api object
        self.bd = None

    def run(self):

        def _update_api_data(data_keys):
            data_dict = {}

            for d in data_keys:
                data_dict[d] = api_data[d]

            self.wallet_instance.data_store.write_value(**data_dict)

        while threading.main_thread().is_alive() and not self.event.is_set():

            addresses = self.wallet_instance.all_addresses

            self.bd = blockchain.blockchain_api(addresses, self.refresh_rate,
                                                source=config.get_value('BLOCKCHAIN_API_SOURCE'))
            price_data = price.BitcoinPrice(currency=config.get_value('FIAT'),
                                            source=config.get_value('PRICE_API_SOURCE'))

            try:
                api_data = {
                    'WALLET_BAL': self.bd.wallet_balance,
                    'TXNS': self.bd.transactions,
                    'ADDRESS_BALS': self.bd.address_balances,
                    'PRICE': price_data.price,
                    'UNSPENT_OUTS': self.bd.unspent_outputs
                }
                self.connection_exception = None
                self.connection_status = self.ApiConnectionStatus.good

                self.connection_timestamp = time.time()
            # TODO IMPLEMENT STANDARD ERROR FOR PRICE TOO. (like BlockchainConnectionError's abstracted exception)
            except (blockchain.BlockchainConnectionError, requests.RequestException) as ex:

                self.connection_exception = ex
                self.connection_status = self.ApiConnectionStatus.error

                self.event.wait(self.refresh_rate)

                continue

            # data that needs to be updated
            old_keys = [k for k in api_data if self.wallet_instance.data_store.get_value(k) != api_data[k]]

            # if old_keys isn't an empty list
            if old_keys and not self.event.is_set():
                _update_api_data(old_keys)

            # if new transactions have been updated, used addresses are set appropriately
            self.wallet_instance.set_used_addresses()

            self.event.wait(self.refresh_rate)


class Wallet:

    @staticmethod
    def get_metadata(name):
        w_info_file = os.path.join(config.WALLET_DATA_DIR, name, config.WALLET_INFO_FILE_NAME)

        with open(w_info_file) as f:
            m_data = json.load(f)

        return m_data

    @classmethod
    def new_wallet(cls, name, password, hd_wallet_obj, offline=False):

        if not isinstance(hd_wallet_obj, hd.HDWallet):
            raise TypeError('hd_wallet_obj must be an instance of Bip32 class')

        dir_ = os.path.join(config.WALLET_DATA_DIR, name)
        data_file_path = os.path.join(dir_, config.WALLET_DATA_FILE_NAME)

        # Everything is in a try/except block so files get cleaned up
        # before exception is raised
        try:

            if not os.path.isdir(dir_):
                os.makedirs(dir_, exist_ok=True)

            elif not is_wallet(name) and os.path.isdir(dir_):
                # won't raise exception if wallet folder exists but doesn't contain any data needed
                pass

            else:
                raise WalletAlreadyExistsError('Wallet with the same name already exists!')

            with open(data_file_path, 'w+'):
                pass

            d_store = data.DataStore(data_file_path, password, data_format=config.STANDARD_DATA_FORMAT,
                                     sensitive_keys=config.SENSITIVE_DATA)

            addresses = hd_wallet_obj.addresses()

            info = {
                'MNEMONIC': hd_wallet_obj.mnemonic,
                'XPRIV': hd_wallet_obj.master_private_key,
                'XPUB': hd_wallet_obj.master_public_key,
                'ACCOUNT_XPUB': hd_wallet_obj.account_public_key,
                'PATH': hd_wallet_obj.path,
                'GAP_LIMIT': hd_wallet_obj.gap_limit,
                'SEGWIT': hd_wallet_obj.is_segwit,
                'ADDRESSES_RECEIVING': addresses[0],
                'ADDRESSES_CHANGE': addresses[1],
                'ADDRESS_WIF_KEYS': hd_wallet_obj.address_wifkey_pairs(),
                'DEFAULT_ADDRESSES': {'receiving': addresses[0], 'change': addresses[1]}
            }

            d_store.write_value(**info)

            del hd_wallet_obj

            with open(os.path.join(dir_, config.WALLET_INFO_FILE_NAME), 'w') as w_info_file:
                w_data = {'watch_only': cls == WatchOnlyWallet}
                json.dump(w_data, w_info_file)

            return cls(name, password, offline=offline)

        except BaseException as ex:

            # if exception is because of a name conflict, it won't delete data
            if not isinstance(ex, WalletAlreadyExistsError):
                shutil.rmtree(dir_, ignore_errors=True)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password, offline=False):
        data_file_path = os.path.join(config.WALLET_DATA_DIR, name, 'wallet_data')
        self.data_store = data.DataStore(data_file_path, password, data_format=config.STANDARD_DATA_FORMAT,
                                         sensitive_keys=config.SENSITIVE_DATA)

        if not offline:
            self.updater_thread = self._create_api_updater_thread(refresh_rate=API_REFRESH_RATE)
            self.updater_thread.start()

        self.name = name

    def _create_api_updater_thread(self, refresh_rate):
        return _ApiDataUpdaterThread(self, refresh_rate)

    def _set_addresses_used(self, addresses):
        r_addrs = self.receiving_addresses
        c_addrs = self.change_addresses
        u_addrs = self.used_addresses

        for address in addresses:

            if address not in r_addrs + c_addrs:
                raise ValueError('Address not found)')

            else:

                if address in r_addrs:
                    addr_index = r_addrs.index(address)
                    u_addrs.append(r_addrs.pop(addr_index))

                else:
                    addr_index = c_addrs.index(address)
                    u_addrs.append(c_addrs.pop(addr_index))

        self.data_store.write_value(**{'ADDRESSES_RECEIVING': r_addrs,
                                       'ADDRESSES_CHANGE': c_addrs,
                                       'ADDRESSES_USED': u_addrs})

    def set_used_addresses(self):
        """ sets all addresses with txns associated with them as used"""
        non_used_addresses = self.receiving_addresses + self.change_addresses

        txns = structs.Transactions.from_list(self.transactions)
        tx_addresses = txns.find_address_txns(non_used_addresses)

        u_addrs = [a for a in non_used_addresses if a in tx_addresses]

        if u_addrs:
            self._set_addresses_used(u_addrs)

    # fee will be modified later using transactions change_fee method, as the
    # size of the transaction is currently unknown
    def make_unsigned_transaction(self, outs_amounts, fee=0, locktime=0):

        if not utils.validate_addresses(a for a in outs_amounts):
            raise ValueError('Invalid address(es) entered')

        if not all(isinstance(i, int) for i in outs_amounts.values()) and isinstance(fee, int):
            raise TypeError('Output values must be positive ints')

        if not all(j > 0 for j in outs_amounts.values()) and fee > 0:
            raise ValueError('Outputs must be > 0')

        txn = tx.Transaction(utxo_data=self.unspent_outputs,
                             outputs_amounts=outs_amounts,
                             change_address=self.change_addresses[0],
                             fee=fee,
                             is_segwit=self.is_segwit,
                             locktime=locktime,
                             use_unconfirmed_utxos=config.get_value('SPEND_UNCONFIRMED_UTXOS'),
                             use_full_address_utxos=not config.get_value('SPEND_UTXOS_INDIVIDUALLY'))

        return txn

    def sign_transaction(self, unsigned_txn, password):

        input_addresses = unsigned_txn.input_addresses
        wif_keys = self.get_wif_keys(password, input_addresses)

        unsigned_txn.sign(wif_keys)

    @staticmethod
    def serialize_transaction(transaction):
        if not isinstance(transaction, tx.Transaction):
            raise ValueError(f'transaction must be an instance of {tx.Transaction.__name__} class')

        return pickle.dumps(transaction)

    @staticmethod
    def deserialize_transaction(txn_bytes):
        """ if unpickling fails, returns None. Raises ValueError if
        deserialized bytes are not instance of tx.Transaction"""
        try:
            obj = pickle.loads(txn_bytes)

            if isinstance(obj, tx.Transaction):
                return obj
            else:
                raise ValueError(f'Un-pickled object is not of type "{tx.Transaction.__name__}"')

        except pickle.PickleError:
            return None

    def export_transaction(self, transaction):
        """ exported transaction in json format """
        txn_bytes = self.serialize_transaction(transaction)
        hex_txn = txn_bytes.hex()

        # xpub key is added as the salt, to add a bit more security
        # to the exported transaction, as pickle can introduce
        # security concerns (e.g. the transaction object could be modified
        # so that different addresses are used, but all public attributes
        # would be the same). But really, users shouldn't just import transactions
        # if they don't know where they came from
        valid_hash = hashlib.sha512(txn_bytes + self.account_xpub.encode('utf-8')).hexdigest()

        txn_data = {
            'txn': hex_txn,
            'hash': valid_hash
        }

        return json.dumps(txn_data)

    @staticmethod
    def _check_transaction_import_format(json_data):
        try:
            d = json.loads(json_data)
            if not all(k in ('txn', 'hash') for k in d.keys()):
                return False

        except json.JSONDecodeError:
            return False

        return True

    def import_transaction(self, json_data):
        """ returns a Transaction object """
        if not self._check_transaction_import_format(json_data):
            raise ValueError('Cannot import transaction: Invalid format')

        txn_data = json.loads(json_data)

        txn_bytes = binascii.unhexlify(txn_data['txn'])
        txn_hash = hashlib.sha512(txn_bytes + self.account_xpub.encode('utf-8')).hexdigest()

        if not txn_data['hash'] == txn_hash:
            raise ValueError('Cannot import transaction: Invalid hash')

        txn = self.deserialize_transaction(txn_bytes)

        if txn is None:
            raise ValueError('Cannot import transaction: deserialization failure')
        else:
            return txn

    def file_export_transaction(self, file_path, transaction):
        """ writes a transaction export to file """
        txn_data = self.export_transaction(transaction)

        with open(file_path, 'w') as f:
            f.write(txn_data)

    def file_import_transaction(self, file_path):
        """ returns a transaction import from file """
        with open(file_path, 'r') as f:
            return self.import_transaction(f.read())

    def clear_cached_api_data(self):
        api_keys = ['TXNS', 'ADDRESS_BALS', 'WALLET_BAL', 'UNSPENT_OUTS', 'PRICE']
        k_v = {k: None for k in api_keys}

        self.data_store.write_value(**k_v)

    @staticmethod
    def broadcast_transaction(signed_txn):
        if not signed_txn.is_signed:
            raise ValueError('Transaction must be signed')

        return blockchain.broadcast_transaction(signed_txn.hex_txn)

    def change_gap_limit(self, new_gap_limit, password):
        if new_gap_limit < GAP_LIMIT_MIN or new_gap_limit > GAP_LIMIT_MAX:
            raise ValueError(f'Gap limit must be between {GAP_LIMIT_MIN} and {GAP_LIMIT_MAX}')

        if not isinstance(new_gap_limit, int):
            raise TypeError('Gap limit must be an int')

        if new_gap_limit > self.gap_limit:
            xpriv = self.get_xpriv(password)

            hd_obj = hd.HDWallet(key=xpriv, path=self.path, segwit=self.is_segwit,
                                 gap_limit=new_gap_limit)

            # only generate new addresses and wif keys
            new_addresses = hd_obj.addresses(start_idx=self.gap_limit)
            new_address_wif_keys = hd_obj.address_wifkey_pairs(start_idx=self.gap_limit)

            r_addresses = self.default_addresses['receiving'] + new_addresses[0]
            c_addresses = self.default_addresses['change'] + new_addresses[1]

            cur_addr_wif_keys = self.get_address_wif_keys(password)
            r_keys = cur_addr_wif_keys['receiving']
            c_keys = cur_addr_wif_keys['change']

            r_keys.update(new_address_wif_keys['receiving'])
            c_keys.update(new_address_wif_keys['change'])

            addr_wif_keys = cur_addr_wif_keys

            del hd_obj

        elif new_gap_limit < self.gap_limit:
            r_addresses = self.default_addresses['receiving'][:new_gap_limit]
            c_addresses = self.default_addresses['change'][:new_gap_limit]

            cur_addr_wif_keys = self.get_address_wif_keys(password)
            addr_wif_keys = {}

            new_r_keys = dict(list(cur_addr_wif_keys['receiving'].items())[:new_gap_limit])
            new_c_keys = dict(list(cur_addr_wif_keys['change'].items())[:new_gap_limit])

            addr_wif_keys.update({'receiving': new_r_keys})
            addr_wif_keys.update({'change': new_c_keys})

        else:
            return

        new_address_data = {
                'GAP_LIMIT': new_gap_limit,
                'ADDRESSES_RECEIVING': r_addresses,
                'ADDRESSES_CHANGE': c_addresses,
                'ADDRESSES_USED': [],
                'ADDRESS_WIF_KEYS': addr_wif_keys,
                'DEFAULT_ADDRESSES': {'receiving': r_addresses, 'change': c_addresses}
        }

        self.data_store.write_value(**new_address_data)

        self.clear_cached_api_data()

    def address_type(self, address, default_type=True):
        """ if default type is True, it will return what the address originally was (ignores used)"""

        if address not in self.all_addresses:
            raise ValueError('Address not in wallet')

        if address in self.receiving_addresses:
            return 'receiving'

        elif address in self.change_addresses:
            return 'change'

        elif address in self.used_addresses and not default_type:
            return 'used'

        elif address in self.used_addresses and default_type:
            return 'receiving' if address in self.default_addresses['receiving'] else 'change'

    @property
    def xpub(self):
        return self.data_store.get_value('XPUB')

    @property
    def account_xpub(self):
        return self.data_store.get_value('ACCOUNT_XPUB')

    @property
    def path(self):
        return self.data_store.get_value('PATH')

    @property
    def gap_limit(self):
        return self.data_store.get_value('GAP_LIMIT')

    @property
    def default_addresses(self):
        return self.data_store.get_value('DEFAULT_ADDRESSES')

    @property
    def receiving_addresses(self):
        return self.data_store.get_value('ADDRESSES_RECEIVING')

    @property
    def change_addresses(self):
        return self.data_store.get_value('ADDRESSES_CHANGE')

    @property
    def used_addresses(self):
        return self.data_store.get_value('ADDRESSES_USED')

    @property
    def all_addresses(self):
        return self.receiving_addresses + self.change_addresses + self.used_addresses

    @property
    def is_segwit(self):
        return self.data_store.get_value('SEGWIT')

    @property
    def address_balances(self):
        return self.data_store.get_value('ADDRESS_BALS')

    @property
    def transactions(self):
        return self.data_store.get_value('TXNS')

    @property
    def price(self):
        # price class should return int by default
        return self.data_store.get_value('PRICE')

    @property
    def wallet_balance(self):
        try:
            return self.data_store.get_value('WALLET_BAL')[0]
        # if wallet_balance is a blank list
        except IndexError:
            return 0

    @property
    def unconfirmed_wallet_balance(self):
        try:
            return self.data_store.get_value('WALLET_BAL')[1]
        # if wallet_balance is a blank list
        except IndexError:
            return 0

    @property
    def fiat_wallet_balance(self):
        """ returns fiat balance rounded to 2 decimal places """
        # wallet balance is in satoshis while price is per BTC (1e8 satoshis)
        return round(((self.wallet_balance / config.UNIT_FACTORS['BTC']) * self.price), 2)

    @property
    def unconfirmed_fiat_wallet_balance(self):
        """ returns fiat balance rounded to 2 decimal places """
        # wallet balance is in satoshis while price is per BTC (1e8 satoshis)
        return round(((self.unconfirmed_wallet_balance / config.UNIT_FACTORS['BTC']) * self.price), 2)

    @property
    def unspent_outputs(self):
        return self.data_store.get_value('UNSPENT_OUTS')

    # attributes below require a password to return

    def get_mnemonic(self, password):

        if self.data_store.validate_password(password):
            return self.data_store.get_value('MNEMONIC')

        else:
            raise data.IncorrectPasswordError

    def get_xpriv(self, password):

        if self.data_store.validate_password(password):
            return self.data_store.get_value('XPRIV')

        else:
            raise data.IncorrectPasswordError

    def get_address_wif_keys(self, password):
        if self.data_store.validate_password(password):
            addr_wif_keys = self.data_store.get_value('ADDRESS_WIF_KEYS')

            r_dict = addr_wif_keys['receiving']
            for k, v in r_dict.items():
                r_dict.update({k: self.data_store.decrypt(v)})

            c_dict = addr_wif_keys['change']
            for K, V in c_dict.items():
                c_dict.update({K: self.data_store.decrypt(V)})

            return addr_wif_keys

        else:
            raise data.IncorrectPasswordError

    def get_wif_keys(self, password, addresses):

        if self.data_store.validate_password(password):
            wif_keys = []
            addr_wif_keys = self.data_store.get_value('ADDRESS_WIF_KEYS')

            for a in addresses:
                addr_type = self.address_type(a)

                # only decrypt the values that we need
                wif_keys.append(self.data_store.decrypt(addr_wif_keys[addr_type][a]))

            return wif_keys

        else:
            raise data.IncorrectPasswordError


class WatchOnlyWallet(Wallet):

    def sign_transaction(self, unsigned_txn, password):
        raise WatchOnlyWalletError

    def get_address_wifkey_pairs(self, password):
        raise WatchOnlyWalletError

    def get_mnemonic(self, password):
        raise WatchOnlyWalletError

    def get_xpriv(self, password):
        raise WatchOnlyWalletError

    def get_wif_keys(self, password, addresses):
        raise WatchOnlyWalletError

    def change_gap_limit(self, new_gap_limit, password):
        if new_gap_limit < GAP_LIMIT_MIN or new_gap_limit > GAP_LIMIT_MAX:
            raise ValueError(f'Gap limit must be between {GAP_LIMIT_MIN} and {GAP_LIMIT_MAX}')

        if not isinstance(new_gap_limit, int):
            raise TypeError('Gap limit must be an int')

        if new_gap_limit > self.gap_limit:

            hd_obj = hd.HDWallet(key=self.account_xpub, path='m', segwit=self.is_segwit,
                                 gap_limit=new_gap_limit)

            # only generate new addresses
            new_addresses = hd_obj.addresses(start_idx=self.gap_limit)

            r_addresses = self.default_addresses['receiving'] + new_addresses[0]
            c_addresses = self.default_addresses['change'] + new_addresses[1]

            del hd_obj

        elif new_gap_limit < self.gap_limit:
            r_addresses = self.default_addresses['receiving'][:new_gap_limit]
            c_addresses = self.default_addresses['change'][:new_gap_limit]

        else:
            return

        new_address_data = {
                'GAP_LIMIT': new_gap_limit,
                'ADDRESSES_RECEIVING': r_addresses,
                'ADDRESSES_CHANGE': c_addresses,
                'ADDRESSES_USED': [],
                'DEFAULT_ADDRESSES': {'receiving': r_addresses, 'change': c_addresses}
        }

        self.data_store.write_value(**new_address_data)

        self.clear_cached_api_data()
