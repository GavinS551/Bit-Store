import time
import datetime
import abc

import requests

from . import btc_verify
from . import config


def blockchain_api(addresses, refresh_rate, source=config.BLOCKCHAIN_API_SOURCE):

    # input validation
    if not isinstance(addresses, list):
        raise ValueError('Address(es) must be in a list!')

    if not btc_verify.check_bc(addresses):
        raise ValueError('Invalid Address entered')

    sources = {
        'blockchain.info': BlockchainInfo
    }

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    return sources[source](addresses, refresh_rate)

# TODO CHANGE ALL METHODS TO USE STANDARD TXN FORMAT, THEN ONLY TRANSACTIONS METHOD WILL BE API SPECIFIC

class BlockchainApiInterface(metaclass=abc.ABCMeta):
    """
    A blockchain api class must accept two arguments: 1. addresses (a list
    of bitcoin addresses i.e a "wallet") and 2. timeout (an int (seconds)
    that sets the refresh rate of the api calls)

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
    def transactions(self):
        """ format: [ {

            'txid': str,
            'date': str,
            'block_height': int,
            'confirmations': int,
            'fee': int,
            'size': int,
            'inputs': [{'value': int, 'address': str, 'n': int}, ...]
            'outputs': [{'value': int, 'address': str, 'n': int, 'spent': bool}, ...]
            'wallet_amount': int

        }, ...]
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def unspent_outputs(self):
        """ format = tuple(txid, output_num, address, script, value) """
        raise NotImplementedError


class BlockchainInfo(BlockchainApiInterface):

    def __init__(self, addresses, refresh_rate):

        self.addresses = addresses
        self.URL = 'https://blockchain.info/multiaddr?active='

        self.last_request_time = 0
        self.last_requested_data = {}

        self.refresh_rate = refresh_rate

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
        if not time.time() - self.last_request_time < self.refresh_rate:

            url = self.URL

            for address in self.addresses:
                url += f'{address}|'

            data = requests.get(url, timeout=10).json()
            self.last_request_time = time.time()
            self.last_requested_data = data

            return data

        else:
            # if 10 seconds haven't passed since last api call, the last
            # data received will be returned
            return self.last_requested_data

    @property
    def transactions(self):
        """ returns all txns associated with the entered addresses in standard format"""
        data = self._blockchain_data
        transactions = []

        for tx in data['txs']:

            transaction = dict()

            transaction['txid'] = tx['hash']

            # getting date as local time from unix timestamp
            utc_time = datetime.datetime.utcfromtimestamp(tx['time'])
            local_time = utc_time.astimezone()
            transaction['date'] = local_time.strftime('%Y-%m-%d %H:%M:%S (%Z)')

            transaction['block_height'] = tx['block_height']

            # if a block isn't confirmed yet, there will be no block_height key
            try:
                transaction['confirmations'] = (self.blockchain_height - tx['block_height']) + 1  # blockchains start at 0
            except KeyError:
                transaction['confirmations'] = 0

            transaction['fee'] = tx['fee']
            transaction['size'] = tx['size']

            ins = []
            for input_ in tx['inputs']:
                i = dict()

                i['value'] = input_['prev_out']['value']
                i['address'] = input_['prev_out']['addr']
                i['n'] = input_['prev_out']['n']

                ins.append(i)

            transaction['inputs'] = ins

            outs = []
            for output in tx['out']:
                o = dict()

                o['value'] = output['value']
                o['address'] = output['addr']
                o['n'] = output['n']
                o['spent'] = output['spent']
                o['script'] = output['script']

                outs.append(o)

            transaction['outputs'] = outs

            # finding the wallet_amount, + or -, for the txn (wallet being all addresses passed into class)
            # i.e the overall change in wallet funds after the txn. any input
            amount = 0
            for i in ins:
                if i['address'] in self.addresses:
                    amount -= i['value']
            for o in outs:
                if o['address'] in self.addresses:
                    amount += o['value']

            transaction['wallet_amount'] = amount

            transactions.append(transaction)

        return transactions

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
    def unspent_outputs(self):
        txns = self.transactions
        utxo_data = []

        for txn in txns:

            for out in txn['outputs']:
                # if the output isn't spent and it relates to an address in self.addresses
                if out['spent'] is False and out['address'] in self.addresses:

                    txid = txn['txid']
                    output_num = out['n']
                    address = out['address']
                    script = out['script']
                    value = out['value']

                    utxo_data.append((txid, output_num, address, script, value))

        return utxo_data

    @property
    def blockchain_height(self):
        return self._blockchain_data['info']['latest_block']['height']
