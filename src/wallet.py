import os

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

            info = {
                'MNEMONIC': bip32_.mnemonic,
                'XPRIV': bip32_.master_private_key,
                'XPUB': bip32_.master_public_key,
                'PATH': bip32_.path,
                'GAP_LIMIT': bip32_.gap_limit,
                'SEGWIT': bip32_.is_segwit,
                'ADDRESSES_RECEIVING': bip32_.addresses()[0],
                'ADDRESSES_CHANGE': bip32_.addresses()[1],
            }

            d_store.write_value(**info)

            # Minimise amount of time sensitive data is in RAM
            del bip32_
            del d_store

            return cls(name, password)

        except:

            if os.path.exists(data_file_path):
                os.remove(data_file_path)
            if os.path.exists(dir_):
                os.rmdir(dir_)

            # re-raise exception that triggered try/except block
            raise

    def __init__(self, name, password):
        data_file_path = os.path.join(config.DATA_DIR, name, 'wallet_data.json')
        self.data_store = data.DataStore(data_file_path, password)

        # NETWORK RELATED FUNCTIONS
        addresses = self.receiving_addresses + self.change_addresses + self.used_addresses
        self.blockchain_api = blockchain.BlockchainInfoAPI(addresses)

        self.fiat_price_api = price.BitcoinPrice(currency=config.FIAT, source=config.PRICE_API_SOURCE)

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
        # TODO: PERFORMANCE IMPROVEMENTS NEEDED
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
