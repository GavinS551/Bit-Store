# Copyright (C) 2018  Gavin Shaughnessy
#
# Bit-Store is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time
import math
import json

import requests

from . import utils, config


class BlockchainConnectionError(Exception):
    pass


# TODO: ADD MORE API SOURCES
def broadcast_transaction(hex_transaction):
    url = 'https://chain.so/api/v2/send_tx/BTC'

    try:
        request = requests.post(url=url, data={'tx_hex': hex_transaction}, timeout=10)

    except requests.RequestException:
        return False, None

    return request.ok, request.status_code


def blockchain_api(addresses, refresh_rate, source, timeout=10):

    sources = {
        'blockchain.info': BlockchainInfo,
        'blockexplorer.com': BlockExplorer
    }

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    source_cls = sources[source]

    if not isinstance(addresses, list):
        raise TypeError('Address(es) must be in a list!')

    if not utils.validate_addresses(addresses, allow_bech32=source_cls.bech32_support):
        raise ValueError('Invalid Address entered')

    return source_cls(addresses, refresh_rate, timeout=timeout)


class EstimateFee:
    """ api interfaces should return a tuple of low, medium and high priority fees, in sat/byte.
     they should also update cached api data every self._refresh_rate seconds.

     raises BlockchainConnectionError if it cannot reach the specified source.
    """

    def __init__(self, source):
        self.sources = {
            'bitcoinfees.earn': self._bitcoinfees_earn
        }

        if source not in self.sources:
            raise NotImplementedError(f'{source} is not an implemented source')

        self.source_method = self.sources[source]

        # unix timestamp of last api request, to maintain 60 second refresh
        self._last_request = 0
        self._cached_fee_info = None
        self._refresh_rate = 60  # seconds

        self.timeout = 10

    @property
    def low_priority(self):
        return self.source_method()[0]

    @property
    def med_priority(self):
        return self.source_method()[1]

    @property
    def high_priority(self):
        return self.source_method()[2]

    def _bitcoinfees_earn(self):
        """ interface for bitcoinfees.earn api """
        if time.time() - self._last_request > self._refresh_rate or self._cached_fee_info is None:
            url = 'https://bitcoinfees.earn.com/api/v1/fees/recommended'

            try:
                request = requests.get(url, timeout=self.timeout)
                data = request.json()

            except (requests.RequestException, json.JSONDecodeError) as ex:
                raise BlockchainConnectionError from ex

            fee_info = (data['hourFee'], data['halfHourFee'], data['fastestFee'])

            self._cached_fee_info = fee_info
            self._last_request = time.time()

            return fee_info

        else:
            return self._cached_fee_info


class _BlockchainBaseClass:
    """ subclasses need to overwrite transactions property and make
     sure it returns transactions in data format seen in doc-string of the property

     Connection errors should be re-raised as BlockchainConnectionError
     """

    bech32_support = None

    def __init__(self, addresses, refresh_rate, timeout=10):

        self.addresses = addresses
        self.timeout = timeout

        self.last_request_time = 0
        self.last_requested_data = {}

        self.refresh_rate = refresh_rate

        self.last_transactions = None
        self.blockchain_data_updated = True

    @property
    def transactions(self):
        """ format: [ {

            'txid': str,
            'date': str,
            'block_height': int or None,
            'confirmations': int,
            'fee': int,
            'size': int,
            'inputs': [{'value': int, 'address': str, 'n': int}, ...],
            'outputs': [{'value': int, 'address': str, 'n': int, 'spent': bool, 'script': str}, ...],
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
        """ returns a dict of addresses/(balances, unconfirmed balances) using UTXO data """

        balances = []
        unspent_outs = self.unspent_outputs

        for address in self.addresses:
            value = 0
            unconfirmed_value = 0

            for utxo in unspent_outs:
                if utxo[2] == address:
                    # if the utxo has 0 confirmations
                    if utxo[5] == 0:
                        unconfirmed_value += utxo[4]
                        unspent_outs.remove(utxo)
                        continue

                    value += utxo[4]
                    unspent_outs.remove(utxo)

            balances.append((address, (value, unconfirmed_value)))

        return dict(balances)

    @property
    def wallet_balance(self):
        """ Combined (balance/unconfirmed balance) of all addresses """
        balance = sum([b[1][0] for b in self.address_balances.items()])
        unconfirmed_balance = sum([b[1][1] for b in self.address_balances.items()])

        return [balance, unconfirmed_balance]

    def txn_wallet_amount(self, transaction):
        """ finding the wallet_amount, + or -, for the txn (wallet being all
        addresses in self.addresses) i.e the overall change in wallet funds
        after the txn.
        """
        # transaction in standard format shown in transactions property docstring
        # (minus wallet_amount of course.)
        amount = 0
        for i in transaction['inputs']:
            if i['address'] in self.addresses:
                amount -= i['value']
        for o in transaction['outputs']:
            if o['address'] in self.addresses:
                amount += o['value']

        return amount


class BlockchainInfo(_BlockchainBaseClass):
    bech32_support = False

    @property
    def _blockchain_data(self):
        # leaves self.refresh rate seconds between api requests
        if time.time() - self.last_request_time > self.refresh_rate:

            url = 'https://blockchain.info/multiaddr?active='

            for address in self.addresses:
                url += f'{address}|'
            url += '&n=100'  # show up to 100 (max) transactions

            try:
                request = requests.get(url, timeout=self.timeout)
                data = request.json()
                request.raise_for_status()

            except (requests.RequestException, json.JSONDecodeError) as ex:
                raise BlockchainConnectionError from ex

            self.last_request_time = time.time()
            self.last_requested_data = data
            self.blockchain_data_updated = True

            return data

        else:
            # if self.refresh_rate seconds haven't passed since last api call,
            # the last data received will be returned
            return self.last_requested_data

    @property
    def transactions(self):
        """ returns all txns associated with the entered addresses in standard format"""
        if not self.blockchain_data_updated and self.last_transactions is not None:
            return self.last_transactions

        data = self._blockchain_data
        transactions = []

        for tx in data['txs']:

            transaction = dict()

            transaction['txid'] = tx['hash']

            transaction['date'] = utils.datetime_str_from_timestamp(tx['time'],
                                                                    config.DATETIME_FORMAT,
                                                                    utc=not config.get_value('USE_LOCALTIME'))

            try:
                transaction['block_height'] = tx['block_height']
            except KeyError:
                transaction['block_height'] = None

            blockchain_height = self._blockchain_data['info']['latest_block']['height']

            # if a block isn't confirmed yet, there will be no block_height key
            try:
                transaction['confirmations'] = (blockchain_height - tx['block_height']) + 1  # blockchains start at 0
            except KeyError:
                transaction['confirmations'] = 0

            transaction['fee'] = tx['fee']
            # vsize should be the same as size for legacy txns
            transaction['vsize'] = math.ceil(tx['weight'] / 4)  # bitcoin core recommends rounding up

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

            transaction['wallet_amount'] = self.txn_wallet_amount(transaction)

            transactions.append(transaction)

        self.last_transactions = transactions
        return transactions


class BlockExplorer(_BlockchainBaseClass):
    bech32_support = False

    @property
    def _blockchain_data(self):
        # leaves self.refresh rate seconds between api requests
        if time.time() - self.last_request_time > self.refresh_rate:

            url = 'https://blockexplorer.com/api/addrs/'

            for address in self.addresses:
                # for trailing comma
                if address != self.addresses[-1]:
                    url += f'{address},'
                else:
                    url += address

            url += '/txs?from=0&to=50'

            try:
                request = requests.get(url, timeout=self.timeout)
                data = request.json()
                request.raise_for_status()

            except (requests.RequestException, json.JSONDecodeError) as ex:
                raise BlockchainConnectionError from ex

            if data['totalItems'] > 50:
                raise RuntimeError('Error: More than 50 transactions detected in this wallet. '
                                   'Support for >50 txns is not yet implemented for the '
                                   'blockexplorer.com API. Please use another API source.')

            self.last_request_time = time.time()
            self.last_requested_data = data
            self.blockchain_data_updated = True

            return data

        else:
            # if self.refresh_rate seconds haven't passed since last api call,
            # the last data received will be returned
            self.blockchain_data_updated = False
            return self.last_requested_data

    @property
    def transactions(self):
        if not self.blockchain_data_updated and self.last_transactions is not None:
            return self.last_transactions

        data = self._blockchain_data
        transactions = []

        # some of blockexplorer's values are in BTC...
        btc_to_sat = lambda x: int(x * 1e8)

        for tx in data['items']:
            transaction = dict()

            transaction['txid'] = tx['txid']

            transaction['date'] = utils.datetime_str_from_timestamp(tx['time'],
                                                                    config.DATETIME_FORMAT,
                                                                    utc=not config.get_value('USE_LOCALTIME'))

            # unconfirmed txns have block height of -1
            if tx['blockheight'] < 0:
                transaction['block_height'] = None
            else:
                transaction['block_height'] = tx['blockheight']

            transaction['confirmations'] = tx['confirmations']

            transaction['fee'] = btc_to_sat(tx['fees'])

            # FIXME: this is only size, blockexplorer doesn't provide txn weight
            transaction['vsize'] = tx['size']

            ins = []
            for input_ in tx['vin']:
                i = dict()

                i['value'] = input_['valueSat']
                # addr will be None if it is a bech32 address
                if input_['addr'] is not None:
                    i['address'] = input_['addr']
                else:
                    i['address'] = 'blockexplorer.com: unparsable address'
                i['n'] = input_['n']

                ins.append(i)

            transaction['inputs'] = ins

            outs = []
            for output in tx['vout']:
                o = dict()

                o['value'] = btc_to_sat(float(output['value']))
                # addresses wont be a key if they are bech32 addresses
                try:
                    o['address'] = output['scriptPubKey']['addresses'][0]
                except KeyError:
                    o['address'] = 'blockexplorer.com: unparsable address'

                o['n'] = output['n']
                o['spent'] = not all([s is None for s in (output['spentTxId'],
                                                          output['spentIndex'],
                                                          output['spentHeight'])])
                o['script'] = output['scriptPubKey']['hex']

                outs.append(o)

            transaction['outputs'] = outs

            transaction['wallet_amount'] = self.txn_wallet_amount(transaction)

            transactions.append(transaction)

        self.last_transactions = transactions
        return transactions
