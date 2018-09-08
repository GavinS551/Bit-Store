import os
import threading
import shutil
import enum
import time
import json

import requests.exceptions

from . import blockchain, config, data, tx, price, hd, structs
from ..exceptions.wallet_exceptions import *


API_REFRESH_RATE = 5
WALLET_DATA_FILE_NAME = 'wallet_data'


class _ApiDataUpdaterThread(threading.Thread):

    class ApiConnectionStatus(enum.Enum):

        good = 0
        first_attempt = 1
        error = 2

    def __init__(self, wallet_instance, refresh_rate):

        if not isinstance(wallet_instance, Wallet):
            raise TypeError('wallet_instance must be an instance of Wallet class')

        if not isinstance(refresh_rate, int):
            raise ValueError('Refresh rate must be an int')

        # due to api request limits
        if refresh_rate < 5:
            raise ValueError('Refresh rate must be at least 5 seconds')

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

    def run(self):

        def _update_api_data(data_keys):
            data_dict = {}

            for d in data_keys:
                data_dict[d] = api_data[d]

            self.wallet_instance.data_store.write_value(**data_dict)

        while threading.main_thread().is_alive() and not self.event.is_set():

            addresses = self.wallet_instance.all_addresses

            bd = blockchain.blockchain_api(addresses, self.refresh_rate, source=config.BLOCKCHAIN_API_SOURCE)
            price_data = price.BitcoinPrice(currency=config.FIAT, source=config.PRICE_API_SOURCE)

            try:
                api_data = {
                    'WALLET_BAL': bd.wallet_balance,
                    'TXNS': bd.transactions,
                    'ADDRESS_BALS': bd.address_balances,
                    'PRICE': price_data.price,
                    'UNSPENT_OUTS': bd.unspent_outputs
                }
                self.connection_exception = None
                self.connection_status = self.ApiConnectionStatus.good

                self.connection_timestamp = time.time()

            except (requests.RequestException, json.JSONDecodeError) as ex:

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

    @classmethod
    def new_wallet(cls, name, password, hd_wallet_obj, offline=False):

        if not isinstance(hd_wallet_obj, hd.HDWallet):
            raise ValueError('hd_wallet_obj must be an instance of Bip32 class')

        dir_ = os.path.join(config.WALLET_DATA_DIR, name)
        data_file_path = os.path.join(dir_, WALLET_DATA_FILE_NAME)

        # Everything is in a try/except block so files get cleaned up
        # before exception is raised
        try:

            if not os.path.isdir(dir_):
                os.makedirs(dir_, exist_ok=True)

            elif not os.path.exists(data_file_path) and os.path.isdir(dir_):
                # won't raise exception if wallet folder exists, but no data file
                pass

            else:
                raise WalletAlreadyExistsError('Wallet with the same name already exists!')

            with open(data_file_path, 'w+'):
                pass

            d_store = data.DataStore(data_file_path, password)

            # only gen addresses once, and not twice for receiving and change
            addresses = hd_wallet_obj.addresses()

            info = {
                'MNEMONIC': hd_wallet_obj.mnemonic,
                'XPRIV': hd_wallet_obj.master_private_key,
                'XPUB': hd_wallet_obj.master_public_key,
                'PATH': hd_wallet_obj.path,
                'GAP_LIMIT': hd_wallet_obj.gap_limit,
                'SEGWIT': hd_wallet_obj.is_segwit,
                'ADDRESSES_RECEIVING': addresses[0],
                'ADDRESSES_CHANGE': addresses[1],
                'ADDRESS_WIF_KEYS': dict(hd_wallet_obj.address_wifkey_pairs())
            }

            d_store.write_value(**info)

            hd_wallet_obj.delete_sensitive_data()
            del hd_wallet_obj

            return cls(name, password, offline=offline)

        except BaseException as ex:

            # if exception is because of a name conflict, it won't delete data
            if not isinstance(ex, WalletAlreadyExistsError):
                shutil.rmtree(dir_, ignore_errors=True)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password, offline=False):
        data_file_path = os.path.join(config.WALLET_DATA_DIR, name, 'wallet_data')
        self.data_store = data.DataStore(data_file_path, password)

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

        txn = tx.Transaction(utxo_data=self.unspent_outputs,
                             outputs_amounts=outs_amounts,
                             change_address=self.change_addresses[0],
                             fee=fee,
                             is_segwit=self.is_segwit,
                             locktime=locktime,
                             use_unconfirmed_utxos=config.SPEND_UNCONFIRMED_UTXOS,
                             use_full_address_utxos=not config.SPEND_UTXOS_INDIVIDUALLY)

        return txn

    def sign_transaction(self, unsigned_txn, password):

        input_addresses = unsigned_txn.input_addresses
        wif_keys = self.get_wif_keys(password, input_addresses)

        unsigned_txn.sign(wif_keys)

    @staticmethod
    def broadcast_transaction(signed_txn):
        if not signed_txn.is_signed:
            raise ValueError('Transaction must be signed')

        return blockchain.broadcast_transaction(signed_txn.hex_txn)

    @property
    def xpub(self):
        return self.data_store.get_value('XPUB')

    @property
    def path(self):
        return self.data_store.get_value('PATH')

    @property
    def gap_limit(self):
        return self.data_store.get_value('GAP_LIMIT')

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
        return int(self.data_store.get_value('PRICE'))

    @property
    def wallet_balance(self):
        return self.data_store.get_value('WALLET_BAL')[0]

    @property
    def unconfirmed_wallet_balance(self):
        return self.data_store.get_value('WALLET_BAL')[1]

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

    def get_wif_keys(self, password, addresses):

        if self.data_store.validate_password(password):
            wif_keys = []
            addr_wif_keys = self.data_store.get_value('ADDRESS_WIF_KEYS')

            for a in addresses:
                # only decrypt the values that we need
                wif_keys.append(self.data_store.decrypt(addr_wif_keys[a]))

            return wif_keys

        else:
            raise data.IncorrectPasswordError


class WatchOnlyWallet(Wallet):
    @classmethod
    def new_wallet(cls, name, password, hd_wallet_obj, offline=False):
        # override
        raise NotImplementedError

    def sign_transaction(self, unsigned_txn, password):
        raise NotImplementedError

    def get_address_wifkey_pairs(self, password):
        raise NotImplementedError

    def get_mnemonic(self, password):
        raise NotImplementedError

    def get_xpriv(self, password):
        raise NotImplementedError

    def get_wif_keys(self, password, addresses):
        raise NotImplementedError
