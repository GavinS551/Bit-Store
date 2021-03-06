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

from . import blockchain, config, data, tx, price, hd, structs, utils
from ..exceptions.wallet_exceptions import *


def get_wallet(name, password, offline=False):
    """ function will return wallet of correct type (normal or watch-only) """
    try:
        watch_only = Wallet.get_metadata(name)['watch_only']

        if watch_only:
            return WatchOnlyWallet(name, password, offline=offline)
        else:
            return Wallet(name, password, offline=offline)

    except FileNotFoundError as ex:
        raise WalletNotFoundError(str(ex)) from ex


def is_wallet(name):
    """ checks if the directory is a valid wallet """
    full_path = lambda w: os.path.join(config.WALLET_DATA_DIR, w)
    return all(f in os.listdir(full_path(name)) for f in (config.WALLET_DATA_FILE_NAME, config.WALLET_INFO_FILE_NAME))


class _ApiDataUpdaterThread(threading.Thread):

    class ApiConnectionStatus(enum.Enum):

        good = 0
        first_attempt = 1
        error = 2

    def __init__(self, wallet_instance, blockchain_refresh_rate, fee_refresh_rate, price_refresh_rate):

        if not isinstance(wallet_instance, Wallet):
            raise TypeError('wallet_instance must be an instance of Wallet class')

        refresh_rates = (blockchain_refresh_rate, fee_refresh_rate, price_refresh_rate)
        if not all(isinstance(r, int) and r > 0 for r in refresh_rates):
            raise TypeError('Refresh rates must be positive ints')

        super().__init__(name='API_DATA_UPDATER')

        # event will be set outside of this class
        self.event = threading.Event()

        self.wallet = wallet_instance

        # minimum refresh rate will be used for wait amount in self.run loop
        self.min_refresh_rate = min([blockchain_refresh_rate, fee_refresh_rate, price_refresh_rate])

        # API interface objects
        self.blockchain_interface = blockchain.blockchain_api(config.get('BLOCKCHAIN_API_SOURCE'),
                                                              self.wallet.all_addresses, blockchain_refresh_rate)

        self.fees_interface = blockchain.fee_api(config.get('FEE_ESTIMATE_SOURCE'), fee_refresh_rate)

        self.price_interface = price.price_api(config.get('PRICE_API_SOURCE'), config.get('FIAT'), price_refresh_rate)

        self.connection_status = self.ApiConnectionStatus.first_attempt
        self.connection_timestamp = 0  # unix timestamp

    def run(self):
        # returns a list of datastore values from input list keys
        get_values = lambda vals: [self.wallet.data_store.get_value(v) for v in vals]

        while threading.main_thread().is_alive() and not self.event.is_set():

            try:
                # formatted for data_store write
                api_data = {
                    'WALLET_BAL': self.blockchain_interface.wallet_balance,
                    'TXNS': self.blockchain_interface.transactions,
                    'ADDRESS_BALS': self.blockchain_interface.address_balances,
                    'UNSPENT_OUTS': self.blockchain_interface.unspent_outputs,
                    'PRICE': self.price_interface.price,
                    'ESTIMATED_FEES': self.fees_interface.all_priorities
                }
                self.connection_status = self.ApiConnectionStatus.good
                self.connection_timestamp = time.time()

            except (blockchain.BlockchainConnectionError, price.BtcPriceConnectionError):
                self.connection_status = self.ApiConnectionStatus.error

            else:
                # if values have changed since last call
                if get_values([k for k in api_data]) != [v for v in api_data.values()]:
                    new_txns = api_data['TXNS'] != self.wallet.data_store.get_value('TXNS')

                    self.wallet.data_store.write_values(**api_data)

                    # if new transactions have been updated, used addresses are set appropriately
                    if new_txns:
                        self.wallet.set_used_addresses()

            # reached if exception was raised in try block as well as normal execution of try block
            self.event.wait(self.min_refresh_rate)

    def stop(self):
        self.event.set()


class Wallet:

    @staticmethod
    def get_metadata(name):
        w_info_file = os.path.join(config.WALLET_DATA_DIR, name, config.WALLET_INFO_FILE_NAME)

        with open(w_info_file) as f:
            m_data = json.load(f)

        return m_data

    @staticmethod
    def get_wallet_path(name):
        return os.path.join(config.WALLET_DATA_DIR, name)

    @classmethod
    def new_wallet(cls, name, password, hd_wallet_obj, offline=False):

        if not isinstance(hd_wallet_obj, hd.HDWallet):
            raise TypeError('hd_wallet_obj must be an instance of Bip32 class')

        wallet_dir_path = cls.get_wallet_path(name)
        wallet_data_file_path = os.path.join(wallet_dir_path, config.WALLET_DATA_FILE_NAME)
        wallet_info_file_path = os.path.join(wallet_dir_path, config.WALLET_INFO_FILE_NAME)

        # Everything is in a try/except block so files get cleaned up
        # before exception is raised
        try:

            if not os.path.isdir(wallet_dir_path):
                os.makedirs(wallet_dir_path, exist_ok=True)

            else:
                raise WalletAlreadyExistsError('Wallet with the same name already exists!')

            d_store = data.DataStore.new_data_store(wallet_data_file_path, password,
                                                    data_format=config.STANDARD_DATA_FORMAT,
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

            d_store.write_values(**info)

            with open(wallet_info_file_path, 'w') as w_info_file:
                w_data = {'watch_only': cls == WatchOnlyWallet}
                json.dump(w_data, w_info_file)

            return cls(name, password, offline=offline)

        except BaseException as ex:

            # if exception is because of a name conflict, it won't delete data
            if not isinstance(ex, WalletAlreadyExistsError):
                shutil.rmtree(wallet_dir_path, ignore_errors=True)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password, offline=False):
        self.name = name

        data_file_path = os.path.join(config.WALLET_DATA_DIR, name, config.WALLET_DATA_FILE_NAME)
        self.data_store = data.DataStore(data_file_path, password,
                                         data_format=config.STANDARD_DATA_FORMAT,
                                         sensitive_keys=config.SENSITIVE_DATA)

        if not offline:
            self.updater_thread = None
            self._start_updater_thread()

    def _start_updater_thread(self):
        self.updater_thread = _ApiDataUpdaterThread(self, config.get('BLOCKCHAIN_API_REFRESH'),
                                                    config.get('FEE_API_REFRESH'),
                                                    config.get('PRICE_API_REFRESH'))
        self.updater_thread.start()

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

        self.data_store.write_values(**{'ADDRESSES_RECEIVING': r_addrs,
                                        'ADDRESSES_CHANGE': c_addrs,
                                        'ADDRESSES_USED': u_addrs})

    def set_used_addresses(self):
        """ sets all addresses with txns associated with them as used"""
        non_used_addresses = self.receiving_addresses + self.change_addresses

        txns = structs.Transactions.from_list(self.transactions)
        tx_addresses = txns.find_address_with_txns(non_used_addresses)

        u_addrs = [a for a in non_used_addresses if a in tx_addresses]

        if u_addrs:
            self._set_addresses_used(u_addrs)

    # fee will be modified later using transactions change_fee method, as the
    # size of the transaction is currently unknown
    def make_unsigned_transaction(self, outs_amounts, fee=0):

        if not utils.validate_addresses(a for a in outs_amounts):
            raise ValueError('Invalid address(es) entered')

        if not all(isinstance(i, int) for i in outs_amounts.values()) and isinstance(fee, int):
            raise TypeError('Output values must be positive ints')

        if not all(j > 0 for j in outs_amounts.values()) and fee > 0:
            raise ValueError('Outputs must be > 0')

        change_address = self.change_addresses[0]

        # ensure that the change_address chosen is unused
        # (is possible if transactions are made in quick succession maybe?
        # it happened during my testing anyway, so here this is.)

        # if there are transactions associated with the change address
        if structs.Transactions.from_list(self.transactions).find_address_with_txns((change_address,)):
            self.set_used_addresses()
            change_address = self.next_change_address()

        txn = tx.Transaction(utxo_data=self.unspent_outputs,
                             outputs_amounts=outs_amounts,
                             change_address=change_address,
                             fee=fee,
                             is_segwit=self.is_segwit,
                             use_unconfirmed_utxos=config.get('SPEND_UNCONFIRMED_UTXOS'),
                             use_full_address_utxos=not config.get('SPEND_UTXOS_INDIVIDUALLY'))

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
            raise TransactionImportError('Cannot import transaction: Invalid format')

        txn_data = json.loads(json_data)

        try:
            txn_bytes = binascii.unhexlify(txn_data['txn'])
        except binascii.Error as ex:
            raise TransactionImportError('Cannot import transaction: odd-length hex string') from ex

        txn_hash = hashlib.sha512(txn_bytes + self.account_xpub.encode('utf-8')).hexdigest()

        if not txn_data['hash'] == txn_hash:
            raise TransactionImportError('Cannot import transaction: Invalid hash')

        txn = self.deserialize_transaction(txn_bytes)

        if txn is None:
            raise TransactionImportError('Cannot import transaction: deserialization failure')
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
        self.data_store.write_values(**k_v)

        # if new addresses were added to wallet, we need to
        # restart api data updater thread
        self.updater_thread.stop()
        self.updater_thread.join()
        self._start_updater_thread()

    @staticmethod
    def broadcast_transaction(signed_txn):
        if not signed_txn.is_signed:
            raise ValueError('Transaction must be signed')

        return blockchain.broadcast_transaction(signed_txn.hex_txn)

    def change_gap_limit(self, new_gap_limit):
        gap_limit_min = 10
        gap_limit_max = 50

        if not gap_limit_min < new_gap_limit < gap_limit_max:
            raise ValueError(f'Gap limit must be between {gap_limit_min} and {gap_limit_max}')

        if not isinstance(new_gap_limit, int):
            raise TypeError('Gap limit must be an int')

        if new_gap_limit > self.gap_limit:
            xpriv = self.data_store.get_value('XPRIV')

            hd_obj = hd.HDWallet(key=xpriv, path=self.path, segwit=self.is_segwit,
                                 gap_limit=new_gap_limit)

            # only generate new addresses and wif keys
            new_addresses = hd_obj.addresses(start_idx=self.gap_limit)
            new_address_wif_keys = hd_obj.address_wifkey_pairs(start_idx=self.gap_limit)

            r_addresses = self.default_addresses['receiving'] + new_addresses[0]
            c_addresses = self.default_addresses['change'] + new_addresses[1]

            cur_addr_wif_keys = self.data_store.get_value('ADDRESS_WIF_KEYS')
            r_keys = cur_addr_wif_keys['receiving']
            c_keys = cur_addr_wif_keys['change']

            r_keys.update(new_address_wif_keys['receiving'])
            c_keys.update(new_address_wif_keys['change'])

            addr_wif_keys = cur_addr_wif_keys

            del hd_obj

        elif new_gap_limit < self.gap_limit:
            r_addresses = self.default_addresses['receiving'][:new_gap_limit]
            c_addresses = self.default_addresses['change'][:new_gap_limit]

            cur_addr_wif_keys = self.data_store.get_value('ADDRESS_WIF_KEYS')
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

        self.data_store.write_values(**new_address_data)

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

    def addr_num_transactions(self, address):
        """ return the number of transactions associated with an address """
        if address not in self.all_addresses:
            raise ValueError(f'"{address}" is not a wallet address')

        num_txns = 0
        for t in self.transactions:
            for i in t['inputs']:
                if i['address'] == address:
                    num_txns += 1
                    break
            else:
                for o in t['outputs']:
                    if o['address'] == address:
                        num_txns += 1
                        break

        return num_txns

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
        # we make sure that all keys are present, so there are
        # no KeyErrors when no api data is present
        bals = {k: v for k, v in zip(self.all_addresses, (([0, 0],) * len(self.all_addresses)))}
        bals.update(self.data_store.get_value('ADDRESS_BALS'))
        return bals

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

    @property
    def estimated_fees(self):
        """ List of low, medium and high priority fees. """
        fees = self.data_store.get_value('ESTIMATED_FEES')

        # for compatibility with functions that expect three indexes, which won't be present
        # before the first api request. It will be initialised in data_store as an empty list.
        # (see wallet balance properties above for the same index problems)
        if len(fees) < 3:
            return -1, -1, -1
        else:
            return fees

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
                r_dict.update({k: self.data_store.crypto.decrypt(v)})

            c_dict = addr_wif_keys['change']
            for K, V in c_dict.items():
                c_dict.update({K: self.data_store.crypto.decrypt(V)})

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
                wif_keys.append(self.data_store.crypto.decrypt(addr_wif_keys[addr_type][a]))

            return wif_keys

        else:
            raise data.IncorrectPasswordError

    # Below methods will increase gap limit if there are no more new addresses
    def next_receiving_address(self):
        gap_limit_increase = 5
        try:
            return self.receiving_addresses[0]

        except IndexError:
            self.change_gap_limit(self.gap_limit + gap_limit_increase)

    def next_change_address(self):
        gap_limit_increase = 5
        try:
            return self.receiving_addresses[0]

        except IndexError:
            self.change_gap_limit(self.gap_limit + gap_limit_increase)


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

    def get_address_wif_keys(self, password):
        raise WatchOnlyWalletError

    def change_gap_limit(self, new_gap_limit):
        gap_limit_min = 15
        gap_limit_max = 50

        if not gap_limit_min < new_gap_limit < gap_limit_max:
            raise ValueError(f'Gap limit must be between {gap_limit_min} and {gap_limit_max}')

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

        self.data_store.write_values(**new_address_data)

        self.clear_cached_api_data()
