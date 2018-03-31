import os

from src import data, bip32, config


class Wallet:

    @classmethod
    def new_wallet(cls, name, password, mnemonic=bip32.Bip32.gen_mnemonic(),
                   mnemonic_passphrase='', force_segwit=False, testnet=False):
        dir_ = os.path.join(config.DATA_DIR, name)

        if not os.path.isdir:
            os.makedirs(dir_, exist_ok=True)
        else:
            raise Exception('Wallet with same name already exists!')

        data_file_path = os.path.join(dir_, 'data.json')
        with open(data_file_path, 'w+'):
            pass

        bip32_ = bip32.Bip32.from_mnemonic(mnemonic=mnemonic, passphrase=mnemonic_passphrase,
                                           force_segwit=force_segwit, testnet=testnet)
        d_store = data.DataStore(data_file_path, password)

        info = {
            'MNEMONIC': bip32_.mnemonic,
            'XPRIV': bip32_.master_private_key,
            'XPUB': bip32_.master_public_key,
            'PATH': bip32_.path,
            'GAP_LIMIT': bip32_.gap_limit,
            'ADDRESSES_RECEIVING': bip32_.addresses()[0],
            'ADDRESSES_CHANGE': bip32_.addresses()[1],
        }

        d_store.write_value(**info)

        del bip32_ # explicitly delete bip32 object after we've finished

        return cls(name, password)

    def __init__(self, wallet_dir_path, password):
        data_file_path = os.path.join(wallet_dir_path, 'data.json')
        self.data_store = data.DataStore(data_file_path, password)

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
        # data needs to be decrypted again as it is in config.SENSITIVE_DATA
        return self.data_store.decrypt(self.data_store.get_value('MNEMONIC'))

    @property
    def xpriv(self):
        # data needs to be decrypted again as it is in config.SENSITIVE_DATA
        return self.data_store.decrypt(self.data_store.get_value('XPRIV'))

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
