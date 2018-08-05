import os
import threading
import shutil

import requests.exceptions

from . import data, bip32, config, blockchain, price, tx
from .exceptions.wallet_exceptions import *


API_REFRESH_RATE = 5


class Wallet:

    def _create_api_updater_thread(self, refresh_rate):
        return self.ApiDataUpdaterThread(self, refresh_rate)

    class ApiDataUpdaterThread(threading.Thread):

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
            self.connection_error = None

        def run(self):

            def _update_api_data(data_keys):
                data_dict = {}

                for d in data_keys:
                    data_dict[d] = api_data[d]

                self.wallet_instance.data_store.write_value(**data_dict)

            while threading.main_thread().is_alive() and not self.event.is_set():

                addresses = self.wallet_instance.all_addresses

                bd = blockchain.blockchain_api(addresses)
                price_data = price.BitcoinPrice()

                try:
                    api_data = {
                        'WALLET_BAL': bd.wallet_balance,
                        'TXNS': bd.address_transactions,
                        'ADDRESS_BALS': bd.address_balances,
                        'PRICE': price_data.price,
                        'UNSPENT_OUTS': bd.unspent_outputs
                    }
                    self.connection_error = False

                except (requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                        requests.exceptions.HTTPError) as ex:

                    self.connection_error = ex

                    self.event.wait(self.refresh_rate)

                    continue

                # data that needs to be updated
                old_keys = [k for k in api_data if self.wallet_instance.data_store.get_value(k) != api_data[k]]

                # if old_keys isn't an empty list
                if old_keys and not self.event.is_set():
                    _update_api_data(old_keys)

                # if new transactions have been updated, used addresses are set appropriately
                self.wallet_instance._set_used_addresses_()

                self.event.wait(self.refresh_rate)

    @classmethod
    def new_wallet(cls, name, password, bip32_obj, offline=False):

        if not isinstance(bip32_obj, bip32.Bip32):
            raise ValueError('bip32_obj must be an instance of Bip32 class')

        dir_ = os.path.join(config.DATA_DIR, name)
        data_file_path = os.path.join(dir_, 'wallet_data')

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
            addresses = bip32_obj.addresses()

            info = {
                'MNEMONIC': bip32_obj.mnemonic,
                'XPRIV': bip32_obj.master_private_key,
                'XPUB': bip32_obj.master_public_key,
                'PATH': bip32_obj.path,
                'GAP_LIMIT': bip32_obj.gap_limit,
                'SEGWIT': bip32_obj.is_segwit,
                'ADDRESSES_RECEIVING': addresses[0],
                'ADDRESSES_CHANGE': addresses[1],
                'ADDRESS_WIF_KEYS': dict(zip(addresses, bip32_obj.wif_keys()))
            }

            d_store.write_value(**info)

            bip32_obj.delete_sensitive_data()
            del bip32_obj

            return cls(name, password, offline=offline)

        except BaseException as ex:

            # if exception is because of a name conflict, it won't delete data
            if not isinstance(ex, WalletAlreadyExistsError):
                shutil.rmtree(dir_, ignore_errors=True)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password, offline=False):
        data_file_path = os.path.join(config.DATA_DIR, name, 'wallet_data')
        self.data_store = data.DataStore(data_file_path, password)

        if not offline:
            self.updater_thread = self._create_api_updater_thread(refresh_rate=API_REFRESH_RATE)
            self.updater_thread.start()

        self.name = name

    def _set_addresses_used(self, addresses):
        r_addrs = self.receiving_addresses
        c_addrs = self.change_addresses
        u_addrs = self.used_addresses

        for address in addresses:

            if address not in r_addrs + c_addrs:
                raise ValueError('Address not found!)')

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

    def _set_used_addresses_(self):
        """ sets all addresses with txns associated with them as used"""
        u_addrs = [a for a in self.non_used_addresses if a in self.transactions]
        self._set_addresses_used(u_addrs)

    # fee will be modified later using transactions change_fee method, as the
    # size of the transaction is currently unknown
    def make_unsigned_transaction(self, outs_amounts, fee=0, locktime=0):

        txn = tx.Transaction(inputs_amounts=self.address_balances,
                             outputs_amounts=outs_amounts,
                             change_address=self.change_addresses[0],
                             fee=fee,
                             is_segwit=self.is_segwit,
                             transaction_data=self.unspent_outputs,
                             locktime=locktime)

        return txn

    def make_signed_transaction(self, password, unsigned_txn):

        input_addresses = unsigned_txn.chosen_inputs
        wif_keys = self.get_wif_keys(password, input_addresses)

        return unsigned_txn.signed_txn(wif_keys)

    def change_gap_limit(self, password):
        if self.data_store.validate_password(password):
            pass

        else:
            raise data.IncorrectPasswordError

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
    def non_used_addresses(self):
        return self.receiving_addresses + self.change_addresses

    @property
    def all_addresses(self):
        return self.non_used_addresses + self.used_addresses

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
        return self.data_store.get_value('PRICE')

    @property
    def wallet_balance(self):
        return self.data_store.get_value('WALLET_BAL')

    @property
    def wallet_fiat_balance(self):
        return (self.wallet_balance * 1e-8) * self.price

    @property
    def unspent_outputs(self):
        return self.data_store.get_value('UNSPENT_OUTS')

    # attributes below require a password to return

    def get_address_wifkey_pairs(self, password):

        if self.data_store.validate_password(password):

            _bip32 = bip32.Bip32(key=self.get_xpriv(password), path=self.path,
                                 segwit=self.is_segwit, gap_limit=self.gap_limit)

            return _bip32.address_wifkey_pairs()

        else:
            raise data.IncorrectPasswordError

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

            return dict(zip(addresses, wif_keys))

        else:
            raise data.IncorrectPasswordError

