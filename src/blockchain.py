import time
import abc

import requests

from . import btc_verify
from . import config


def blockchain_api(addresses, source=config.BLOCKCHAIN_API_SOURCE, timeout=10):

    sources = {
        'blockchain.info': BlockchainInfo
    }

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    return sources[source](addresses, timeout)


class BlockchainApiInterface(metaclass=abc.ABCMeta):
    """
    A blockchain api class must accept two arguments: 1. addresses (a list
    of bitcoin addresses) and 2. timeout (an int (seconds) that sets the timeout
    for an api call)

    BALANCES SHOULD ALWAYS BE IN SATOSHIS, AS AN INT
    """

    @property
    @abc.abstractmethod
    def wallet_balance(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def address_balances(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def address_transactions(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def unspent_outputs(self):
        raise NotImplementedError


class BlockchainInfo(BlockchainApiInterface):

    def __init__(self, addresses, timeout=10):

        self.TIME_INTERVAL = 10  # leaves 10 seconds between api requests

        if not isinstance(addresses, list):
            raise ValueError('Address(es) must be in a list!')

        if not btc_verify.check_bc(addresses):
            raise ValueError('Invalid Address entered')

        self.addresses = addresses
        self.URL = 'https://blockchain.info/multiaddr?active='

        self.last_request_time = 0
        self.last_requested_data = {}

        self.timeout = timeout

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

            data = requests.get(url, timeout=self.timeout).json()
            self.last_request_time = time.time()
            self.last_requested_data = data

            return data

        else:
            # if 10 seconds haven't passed since last api call, the last
            # data received will be returned
            return self.last_requested_data

    @property
    def _address_num_transactions(self):
        """ Returns a list of tuples containing address/amount of txns """
        num_txns = []
        for address in self.addresses:
            num_txns.append(self._find_address_data(address, 'n_tx'))

        return list(zip(self.addresses, num_txns))

    @property
    def wallet_balance(self):
        """ Combined balance of all addresses (in satoshis)"""
        return self._blockchain_data['wallet']['final_balance']

    @property
    def address_balances(self):
        """ returns a list of tuples with address/balance(in satoshis) """
        balances = {}
        for address in self.addresses:
            balances[address] = self._find_address_data(address, 'final_balance')

        return balances

    @property
    def address_transactions(self):
        """ Returns a dict with addresses as keys and all txns associated with them as values"""

        # number of total txns needed so the correct amount of txns are added to the txns list
        num_txns = 0

        # addr_num_txns is created because I will be calling it twice, and don't
        # want a second API call to possibly happen like it could calling self._address_num_transactions
        addr_num_txns = self._address_num_transactions
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

    @property
    def unspent_outputs(self):

        unspent_outs = {}
        addr_txns = self.address_transactions

        for address in self.addresses:

            if address in addr_txns:
                address_txns = addr_txns[address]
            else:
                continue

            addr_unspent_outs = []

            for tx in address_txns:
                for out in tx['out']:
                    if out['spent'] is False:
                        addr_unspent_outs.append(out)

            # continue if there is no unspent outs for a particular address
            if not addr_unspent_outs:
                continue

            unspent_outs[address] = addr_unspent_outs

        return unspent_outs
