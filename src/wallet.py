import os
import threading
import time

import requests.exceptions

from . import data, bip32, config, blockchain, price
from .exceptions.wallet_exceptions import *


class Wallet:

    @classmethod
    def new_wallet(cls, name, password, mnemonic=bip32.Bip32.gen_mnemonic(),
                   mnemonic_passphrase='', segwit=True, testnet=False):

        dir_ = os.path.join(config.DATA_DIR, name)
        data_file_path = os.path.join(dir_, 'wallet_data.json')

        # Everything is in a try/except block so files get cleaned up
        # before exception is raised
        try:

            bip32_ = bip32.Bip32.from_mnemonic(mnemonic=mnemonic, passphrase=mnemonic_passphrase,
                                               segwit=segwit, testnet=testnet)

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

            return cls(name, password)

        except BaseException as ex:

            # if exception is because of a name conflict, it won't delete data
            if isinstance(ex, type(WalletAlreadyExistsError)):

                if os.path.exists(data_file_path):
                    os.remove(data_file_path)
                if os.path.exists(dir_):
                    os.rmdir(dir_)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password):
        data_file_path = os.path.join(config.DATA_DIR, name, 'wallet_data.json')
        self.data_store = data.DataStore(data_file_path, password)

        t1 = threading.Thread(target=self._blockchain_data_updater)
        t1.start()

    def _blockchain_data_updater(self):

        # TODO: ADD WRITING DATA PROTECTION WHEN EXITING THREAD

        writing_data = False  # flag that makes sure thread won't end while writing

        def _update_api_data(data_keys):
            data_dict = {}
            global writing_data

            for d in data_keys:
                data_dict[d] = api_data[d]

            writing_data = True
            print('UPDATING API DATA')
            self.data_store.write_value(**data_dict)

            writing_data = False

        api_data = {}

        while True:

            print('UPDATING DATA')

            try:
                addresses = self.receiving_addresses + self.change_addresses + self.used_addresses
                bd = blockchain.BlockchainInfoAPI(addresses)
                price_data = price.BitcoinPrice(currency=config.FIAT, source=config.PRICE_API_SOURCE)

            except requests.exceptions.ConnectionError:
                print('CONNECTION ERROR, TRYING AGAIN IN 30 SECONDS...')
                time.sleep(30)
                continue

            api_data = {
                'WALLET_BAL': bd.wallet_balance,
                'TXNS': bd.address_transactions,
                'ADDRESS_BALS': bd.address_balances,
                'PRICE': price_data.get_price(),
                'UNSPENT_OUTS': bd.unspent_outputs
            }

            print(api_data)

            # data that needs to be updated
            old_keys = [k for k in api_data if self.data_store.get_value(k) != api_data[k]]

            if not old_keys:
                _update_api_data(old_keys)

            time.sleep(10)

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
