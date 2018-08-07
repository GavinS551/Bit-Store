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
            'outputs': [{'value': int, 'address': str, 'n': int}, ...]
            'wallet_amount': int

        }, ...]
        """
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def unspent_outputs(self):
        """ format = tuple(txid, out_num, address, scriptPubKey{hex string}, value) """
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
    def _address_num_transactions(self):
        """ Returns a list of tuples containing address/amount of txns """
        num_txns = []
        for address in self.addresses:
            num_txns.append(self._find_address_data(address, 'n_tx'))

        return list(zip(self.addresses, num_txns))

    @property
    def _address_transactions(self):
        """ Returns a dict with addresses as keys and all txns associated with them as values"""

        txns = []

        for tx in self._blockchain_data['txs']:
            txns.append(tx)

        addresses_with_txns = [a for a, n in self._address_num_transactions if n > 0]

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
    def transactions(self):
        """ returns all txns associated with the entered addresses in standard format"""
        data = self._blockchain_data
        transactions = []

        for tx in data['txs']:

            transaction = {}

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
                i = {}

                i['value'] = input_['prev_out']['value']
                i['address'] = input_['prev_out']['addr']
                i['n'] = input_['prev_out']['n']

                ins.append(i)

            transaction['inputs'] = ins

            outs = []
            for output in tx['out']:
                o = {}

                o['value'] = output['value']
                o['address'] = output['addr']
                o['n'] = output['n']

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
    def unspent_outputs(self):

        unspent_outs = {}
        addr_txns = self._address_transactions

        for address in self.addresses:

            if address in addr_txns:
                address_txns = addr_txns[address]
            else:
                continue

            addr_unspent_outs = []

            for tx in address_txns:
                for out in tx['out']:
                    if out['spent'] is False and out['addr'] == address:
                        addr_unspent_outs.append(tx)

            # continue if there is no unspent outs for a particular address
            if not addr_unspent_outs:
                continue

            unspent_outs[address] = addr_unspent_outs

        utxo_data = []
        for addr, data in unspent_outs.items():

            # getting tx ids and output number for all UTXOs to be spent
            for tx in data:

                # getting the transaction id
                txid = tx['hash']

                # variables will be None if they aren't assigned in below loop
                out_num = None
                scriptpubkey = None
                value = None

                for out in tx['out']:
                    if out['addr'] == addr:
                        out_num = out['n']
                        scriptpubkey = out['script']
                        value = out['value']  # value of output in satoshis

                        break

                utxo_data.append((txid, out_num, addr, scriptpubkey, value))

        return utxo_data

    @property
    def blockchain_height(self):
        return self._blockchain_data['info']['latest_block']['height']
