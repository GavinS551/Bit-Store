import time

import requests


class BlockchainInfoAPI:

    def __init__(self, addresses):

        if not isinstance(addresses, list):
            raise ValueError('Address(es) must be in a list!')

        self.addresses = addresses
        self.URL = 'https://blockchain.info/multiaddr?active='

        self._blockchain_data = self._get_blockchain_data()
        self.last_request = 0

    def _get_blockchain_data(self):
        # leave 10 seconds between api requests
        if not time.time() - self.last_request < 10:
            url = self.URL
            for address in self.addresses:
                url += f'{address}|'

            return requests.get(url).json()

        else:
            # if 10 seconds haven't passed since last api call, the last
            # data received will be returned
            return self._blockchain_data


if __name__ == '__main__':

    addresses = ['3MrYpTRyKU3xoATozbkfWsrjx6FopbEfBz', '32W1cJzQTH6D6TNtVzznMu9NmB3dSvrjpR']
    b = BlockchainInfoAPI(addresses)
