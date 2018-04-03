import time

import requests

from src import btc_verify


class BlockchainInfoAPI:

    def __init__(self, addresses):

        if not isinstance(addresses, list):
            raise ValueError('Address(es) must be in a list!')

        if not btc_verify.check_bc(addresses):
            raise ValueError('Invalid Address entered')

        self.addresses = addresses
        self.URL = 'https://blockchain.info/multiaddr?active='

        self.last_request_time = 0
        self.last_requested_data = {}

    @property
    def _blockchain_data(self):
        # leaves 10 seconds between api requests
        if not time.time() - self.last_request_time < 10:

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

    def _find_address_index(self, address):
        """ this is needed due to blockchain.info not sorting addresses
            in the order they are passed in through the url """

        if address not in self.addresses:
            raise ValueError('Address entered is not in self.addresses')

        for e, i in enumerate(self._blockchain_data['addresses']):
            if i['address'] == address:
                return e

    @property
    def wallet_balance(self):
        """ Combined balance of all addresses (in satoshis)"""
        return self._blockchain_data['wallet']['final_balance']

    @property
    def address_balances(self):
        """ returns a list of tuples with address/balance(in satoshis) """
        balances = []
        for address in self.addresses:
            balances.append(self._blockchain_data['addresses']
                            [self._find_address_index(address)]
                            ['final_balance'])

        return list(zip(self.addresses, balances))


if __name__ == '__main__':

    addresses = ['3MrYpTRyKU3xoATozbkfWsrjx6FopbEfBz', '32W1cJzQTH6D6TNtVzznMu9NmB3dSvrjpR']
    b = BlockchainInfoAPI(addresses)
    print(b.address_balances)
