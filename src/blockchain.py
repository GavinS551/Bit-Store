import time

import requests

from src import btc_verify


class BlockchainInfoAPI:

    def __init__(self, addresses):

        self.TIME_INTERVAL = 10  # leaves 10 seconds between api requests

        if not isinstance(addresses, list):
            raise ValueError('Address(es) must be in a list!')

        if not btc_verify.check_bc(addresses):
            raise ValueError('Invalid Address entered')

        self.addresses = addresses
        self.URL = 'https://blockchain.info/multiaddr?active='

        self.last_request_time = 0
        self.last_requested_data = {}

    def _check_address(self, address):
        if address not in self.addresses:
            raise ValueError('Address entered is not in self.addresses')

    def _find_address_index(self, address):
        """ this is needed due to blockchain.info not sorting addresses
            in the order they are passed in through the url """
        self._check_address(address)

        for e, i in enumerate(self._blockchain_data['addresses']):
            if i['address'] == address:
                return e

    def _find_address_data(self, address, data):
        self._check_address(address)

        if data not in self._blockchain_data['addresses'][self._find_address_index(address)]:
            raise ValueError(f'Data type:{data} is not a valid data type')
        else:
            return self._blockchain_data['addresses'][self._find_address_index(address)][data]

    @property
    def _blockchain_data(self):
        # leaves TIME_INTERVAL seconds between api requests
        if not time.time() - self.last_request_time < self.TIME_INTERVAL:

            url = self.URL

            for address in self.addresses:
                url += f'{address}|'

            data = requests.get(url).json()
            self.last_request_time = time.time()
            self.last_requested_data = data

            return data

        else:
            # if 10 seconds haven't passed since last api call, the last
            # data received will be returned
            return self.last_requested_data

    @property
    def wallet_balance(self):
        """ Combined balance of all addresses (in satoshis)"""
        return self._blockchain_data['wallet']['final_balance']

    @property
    def address_balances(self):
        """ returns a list of tuples with address/balance(in satoshis) """
        balances = []
        for address in self.addresses:
            balances.append(self._find_address_data(address, 'final_balance'))

        return list(zip(self.addresses, balances))

    @property
    def address_num_transactions(self):
        """ Returns a list of tuples containing address/amount of txns """
        num_txns = []
        for address in self.addresses:
            num_txns.append(self._find_address_data(address, 'n_tx'))

        return list(zip(self.addresses, num_txns))

    @property
    def address_transactions(self):
        """ Returns a dict with addresses as keys and all txns associated with them as values"""

        # number of total txns needed so the correct amount of txns are added to the txns list
        num_txns = 0

        # addr_num_txns is created because I will be calling it twice, and don't
        # want a second API call to possibly happen like it could calling self.address_num_transactions
        addr_num_txns = self.address_num_transactions
        for _, n in addr_num_txns:
            num_txns += n

        txns = []
        for i in range(num_txns):
            txns.append(self._blockchain_data['txs'][i])

        addresses_with_txns = [a for a, n in addr_num_txns if n > 0]

        transaction_dict = {}
        for a in addresses_with_txns:
            tx_list = []

            for tx in txns:
                # flag used to make sure a txn won't be added twice if an address
                # acted as both an input and as an output. I.E if an address
                # is in both tx['inputs'] and tx['out']
                tx_caught_flag = False

                for i in tx['inputs']:
                    if a == i['prev_out']['addr']:
                        tx_list.append(tx)
                        tx_caught_flag = True

                if not tx_caught_flag:
                    for i in tx['out']:
                        if a == i['addr']:
                            tx_list.append(tx)

            transaction_dict[a] = tx_list

        return transaction_dict

    def get_unspent_outputs(self, address):
        self._check_address(address)

        if address in self.address_transactions:
            address_txns = self.address_transactions[address]
        else:
            return None

        unspent_outs = []

        for tx in address_txns:
            for out in tx['out']:
                if out['spent'] is False:
                    unspent_outs.append(out)

        return unspent_outs
