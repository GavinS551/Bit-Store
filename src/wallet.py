import os
import threading
import signal
import sys

import requests.exceptions

from . import data, bip32, config, blockchain, price
from .exceptions.wallet_exceptions import *


class Wallet:

    def _create_api_updater_thread(self, refresh_rate):
        return type(self).ApiDataUpdaterThread(self, refresh_rate)

    class ApiDataUpdaterThread(threading.Thread):

        def __init__(self, wallet_instance, refresh_rate):

            if not isinstance(wallet_instance, Wallet):
                raise TypeError('wallet_instance must be an instance of Wallet class')

            if not isinstance(refresh_rate, int):
                raise ValueError('Refresh rate must be an int')

            # due to api request limits
            if refresh_rate < 10:
                raise ValueError('Refresh rate must be at least 10 seconds')

            super().__init__(name='API_DATA_UPDATER')
            self.event = threading.Event()
            self.wallet_instance = wallet_instance
            self.refresh_rate = refresh_rate
            # a requests Exception, stored if the last data request failed
            self.connection_error = None

            self.set_handlers()

        def set_handlers(self):

            def _handler(_, __):
                self.event.set()
                sys.exit(0)

            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)

        def run(self):

            def _update_api_data(data_keys):
                data_dict = {}

                for d in data_keys:
                    data_dict[d] = api_data[d]

                self.wallet_instance.data_store.write_value(**data_dict)

            # if the main thread is dead then self.event can never change as
            # only a SIGINT or SIGTERM from the main thread can set self.event
            while not self.event.is_set() and threading.main_thread().is_alive():

                addresses = self.wallet_instance.receiving_addresses + \
                            self.wallet_instance.change_addresses + \
                            self.wallet_instance.used_addresses

                bd = blockchain.blockchain_api(config.BLOCKCHAIN_API_SOURCE, addresses)
                price_data = price.BitcoinPrice(currency=config.FIAT, source=config.PRICE_API_SOURCE)

                try:
                    api_data = {
                        'WALLET_BAL': int(bd.wallet_balance),
                        'TXNS': bd.address_transactions,
                        'ADDRESS_BALS': bd.address_balances,
                        'PRICE': float(price_data.price),
                        'UNSPENT_OUTS': bd.unspent_outputs
                    }
                    self.connection_error = None

                except (requests.exceptions.ConnectionError,
                        requests.exceptions.Timeout,
                        requests.exceptions.HTTPError) as ex:

                    self.connection_error = ex
                    self.event.wait(30)
                    continue

                # data that needs to be updated
                old_keys = [k for k in api_data if self.wallet_instance.data_store.get_value(k) != api_data[k]]

                # if old_keys isn't an empty list
                if old_keys and not self.event.is_set():
                    _update_api_data(old_keys)

                self.event.wait(self.refresh_rate)

    @classmethod
    def new_wallet(cls, name, password, bip32_obj, offline=False):

        if not isinstance(bip32_obj, bip32.Bip32):
            raise ValueError('bip32_obj must be an instance of Bip32 class')

        dir_ = os.path.join(config.DATA_DIR, name)
        data_file_path = os.path.join(dir_, 'wallet_data.json')

        # Everything is in a try/except block so files get cleaned up
        # before exception is raised
        try:

            bip32_ = bip32_obj

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
            addresses = bip32_.addresses()

            info = {
                'MNEMONIC': bip32_.mnemonic,
                'XPRIV': bip32_.master_private_key,
                'XPUB': bip32_.master_public_key,
                'PATH': bip32_.path,
                'GAP_LIMIT': bip32_.gap_limit,
                'SEGWIT': bip32_.is_segwit,
                'ADDRESSES_RECEIVING': addresses[0],
                'ADDRESSES_CHANGE': addresses[1],
            }

            d_store.write_value(**info)

            # Minimise amount of time sensitive data is in RAM
            del bip32_
            del d_store

            return cls(name, password, offline=offline)

        except BaseException as ex:

            # if exception is because of a name conflict, it won't delete data
            if not isinstance(ex, WalletAlreadyExistsError):

                if os.path.exists(data_file_path):
                    os.remove(data_file_path)
                if os.path.exists(dir_):
                    os.rmdir(dir_)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password, offline=False):
        data_file_path = os.path.join(config.DATA_DIR, name, 'wallet_data.json')
        self.data_store = data.DataStore(data_file_path, password)

        # offline for debugging purposes
        if not offline:
            self.updater_thread = self._create_api_updater_thread(refresh_rate=10)
            self.updater_thread.start()

    def set_address_used(self, address):
        r_addrs = self.receiving_addresses
        c_addrs = self.change_addresses
        u_addrs = self.used_addresses

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

    # CLASS PROPERTIES

    @property
    def mnemonic(self):
        return self.data_store.get_value('MNEMONIC')

    @property
    def xpriv(self):
        return self.data_store.get_value('XPRIV')

    @property
    def address_wifkey_pairs(self):
        _bip32 = bip32.Bip32(key=self.xpriv, path=self.path,
                             segwit=self.is_segwit, gap_limit=self.gap_limit)
        pairs = _bip32.address_wifkey_pairs()

        del _bip32
        return pairs

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
    def unspent_outputs(self):
        return self.data_store.get_value('UNSPENT_OUTS')
