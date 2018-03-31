import os

from src import data, bip32, config

#TODO: use double encryption on certain values like mnemonic, so sensitive
#TODO: data isnt stored in ram unencrypted

# when setting used address, you dont have to make used wif_key. figure out
# some way of doing it then double encryption of wif keys will be easier


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
            'WIFKEYS_RECEIVING': bip32_.wif_keys()[0],
            'WIFKEYS_CHANGE': bip32_.wif_keys()[1]
        }

        d_store.write_value(**info)

        return cls(name, password)

    def __init__(self, wallet_dir_path, password):
        data_file_path = os.path.join(wallet_dir_path, 'data.json')
        self.data_store = data.DataStore(data_file_path, password)

        # always use xpriv here in case passphrase was used with mnemonic at generation
        self.bip32 = bip32.Bip32(self.xpriv)

    def set_address_used(self, address):
        r_addrs = self.receiving_addresses
        c_addrs = self.change_addresses
        u_addrs = self.used_addresses

        r_wif = self.receiving_wif_keys
        c_wif = self.change_wif_keys
        u_wif = self.used_wif_keys

        if address not in r_addrs + c_addrs:
            raise ValueError('Address not found!)')
        else:
            if address in r_addrs:
                addr_index = r_addrs.index(address)
                u_addrs.append(r_addrs.pop(addr_index))
                u_wif.append(r_wif.pop(addr_index))
            else:
                addr_index = c_addrs.index(address)
                u_addrs.append(c_addrs.pop(addr_index))
                u_wif.append(c_wif.pop(addr_index))

        self.data_store.write_value(**{'ADDRESSES_RECEIVING': r_addrs,
                                       'ADDRESSES_CHANGE': c_addrs,
                                       'ADDRESSES_USED': u_addrs,
                                       'WIFKEYS_RECEIVING': r_wif,
                                       'WIFKEYS_CHANGE': c_wif,
                                       'WIFKEYS_USED': u_wif})

    # CLASS PROPERTIES

    @property
    def mnemonic(self):
        return self.data_store.get_value('MNEMONIC')

    @property
    def xpriv(self):
        return self.data_store.get_value('XPRIV')

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
    def receiving_wif_keys(self):
        return self.data_store.get_value('WIFKEYS_RECEIVING')

    @property
    def change_wif_keys(self):
        return self.data_store.get_value('WIFKEYS_CHANGE')

    @property
    def used_wif_keys(self):
        return self.data_store.get_value('WIFKEYS_USED')

    # @property
    # def btc_price(self):
    #     return self.data_store.get_value('BTC_PRICE')


if __name__ == '__main__':
    w = Wallet(r'C:\Users\Gavin Shaughnessy\Desktop', 'helllo')
