import time
import datetime

import requests

from . import btc_verify, config


def blockchain_api(addresses, refresh_rate, source):

    # input validation
    if not isinstance(addresses, list):
        raise ValueError('Address(es) must be in a list!')

    if not btc_verify.check_bc(addresses):
        raise ValueError('Invalid Address entered')

    sources = {
        'blockchain.info': (BlockchainInfo, 'https://blockchain.info/multiaddr?active=')
    }

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    source_cls = sources[source][0]
    source_url = sources[source][1]

    return source_cls(addresses, refresh_rate, source_url)


class _BlockchainBaseClass:
    """ subclasses need to overwrite transactions property and make
     sure it returns transactions in data format seen in doc-string of the property"""

    def __init__(self, addresses, refresh_rate, url):

        self.addresses = addresses
        self.url = url

        self.last_request_time = 0
        self.last_requested_data = {}

        self.refresh_rate = refresh_rate

    @property
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
    def unspent_outputs(self):
        """ returns a list of UTXOs in standard format"""
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
                    confirmations = txn['confirmations']

                    utxo_data.append([txid, output_num, address, script, value, confirmations])

        return utxo_data

    @property
    def address_balances(self):
        """ returns a dicts of addresses/balances(in satoshis) using UTXO data """

        balances = []
        unspent_outs = self.unspent_outputs

        for address in self.addresses:
            value = 0

            for utxo in unspent_outs:
                if utxo[2] == address:
                    value += utxo[4]
                    unspent_outs.remove(utxo)

            balances.append((address, value))

        return dict(balances)

    @property
    def wallet_balance(self):
        """ Combined balance of all addresses (in satoshis)"""
        return sum([b[1] for b in self.address_balances.items()])


class BlockchainInfo(_BlockchainBaseClass):

    @property
    def _blockchain_data(self):
        # leaves self.refresh rate seconds between api requests
        if not time.time() - self.last_request_time < self.refresh_rate:

            url = self.url

            for address in self.addresses:
                url += f'{address}|'
            url += '&n=100'  # show up to 100 (max) transactions

            data = requests.get(url, timeout=10).json()
            self.last_request_time = time.time()
            self.last_requested_data = data

            return data

        else:
            # if self.refresh_rate seconds haven't passed since last api call,
            # the last data received will be returned
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
            transaction['date'] = local_time.strftime(config.DATETIME_FORMAT)

            transaction['block_height'] = tx['block_height']

            blockchain_height = self._blockchain_data['info']['latest_block']['height']

            # if a block isn't confirmed yet, there will be no block_height key
            try:
                transaction['confirmations'] = (blockchain_height - tx['block_height']) + 1  # blockchains start at 0
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
            # i.e the overall change in wallet funds after the txn.
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
