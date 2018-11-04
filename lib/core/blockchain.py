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
import functools

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


def blockchain_api(source, addresses, refresh_rate, timeout=10):

    if not isinstance(addresses, list):
        raise TypeError('Address(es) must be in a list!')

    sources = {
        'blockchain.info': BlockchainInfo,
        'blockexplorer.com': BlockExplorer
    }

    # ensure that all possible sources are implemented
    assert all(s in sources for s in config.POSSIBLE_BLOCKCHAIN_API_SOURCES)

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    source_cls = sources[source]

    if not utils.validate_addresses(addresses, allow_bech32=source_cls.bech32_support):
        raise ValueError('Invalid Address entered')

    return source_cls(addresses, refresh_rate, timeout=timeout)


def fee_api(source, refresh_rate, timeout=10):
    sources = {
        'bitcoinfees.earn': BitcoinFeesEarn
    }

    # ensure all possible sources are implemented
    assert all(s in sources for s in config.POSSIBLE_FEE_ESTIMATE_SOURCES)

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    return sources[source](refresh_rate, timeout)


class _EstimateFeeBaseClass:
    """ api interfaces should return a tuple of low, medium and high priority fees, in sat/byte.
     they should also update cached api data every self._refresh_rate seconds.

     sub-classes should raise BlockchainConnectionError if it cannot connect to the specified source.

     sub-classes need to implement all_priorities property, that returns a list with three values:
     low, medium and high priority fees in sat/byte
    """

    def __init__(self, refresh_rate, timeout):
        self.refresh_rate = refresh_rate  # seconds
        self.timeout = timeout

    def limit_requests(func):
        """ limits requests to once every self._refresh_rate seconds. if it hasn't
        been self._refresh_rate seconds yet, the cached value is returned. should be
        used on methods that make the api calls to website sources
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # initialise cache values
            if not hasattr(self, 'last_request_time'):
                self.last_request_time = 0
            if not hasattr(self, 'cached_fee_info'):
                self.cached_fee_info = None

            if time.time() - self.last_request_time > self.refresh_rate:
                data = func(self, *args, **kwargs)

                self.cached_fee_info = data
                self.last_request_time = time.time()

                return data
            else:
                return self.cached_fee_info

        return wrapper

    @property
    def low_priority(self):
        return self.all_priorities[0]

    @property
    def med_priority(self):
        return self.all_priorities[1]

    @property
    def high_priority(self):
        return self.all_priorities[2]

    @property
    def all_priorities(self):
        raise NotImplementedError


class BitcoinFeesEarn(_EstimateFeeBaseClass):

    @_EstimateFeeBaseClass.limit_requests
    def _bitcoinfees_earn(self):
        """ interface for bitcoinfees.earn api """

        url = 'https://bitcoinfees.earn.com/api/v1/fees/recommended'

        try:
            request = requests.get(url, timeout=self.timeout)
            data = request.json()

        except (requests.RequestException, json.JSONDecodeError) as ex:
            raise BlockchainConnectionError from ex

        fee_info = [data['hourFee'], data['halfHourFee'], data['fastestFee']]

        return fee_info

    @property
    def all_priorities(self):
        return self._bitcoinfees_earn()


class _BlockchainBaseClass:
    """ subclasses need to overwrite transactions property and make
     sure it returns transactions in data format seen in doc-string of the property

     Connection errors should be re-raised as BlockchainConnectionError
     """

    bech32_support = None

    def __init__(self, addresses, refresh_rate, timeout):

        self.addresses = addresses
        self.timeout = timeout

        self.refresh_rate = refresh_rate

        self.last_transactions = None
        self.blockchain_data_updated = True

    def limit_requests(func):
        """ limits a function call to once every self.refresh_rate seconds,
        used for methods that make api calls
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # initialise cache values
            if not hasattr(self, 'last_request_time'):
                self.last_request_time = 0
            if not hasattr(self, 'last_requested_data'):
                self.last_requested_data = {}

            if time.time() - self.last_request_time > self.refresh_rate:
                data = func(self, *args, **kwargs)

                self.last_requested_data = data
                self.last_request_time = time.time()

                self.blockchain_data_updated = True
                return data

            else:
                self.blockchain_data_updated = False
                return self.last_requested_data

        return wrapper

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

                    else:
                        value += utxo[4]

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
    @_BlockchainBaseClass.limit_requests
    def _blockchain_data(self):
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

        return data

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
                                                                    utc=not config.get('USE_LOCALTIME'))

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
    @_BlockchainBaseClass.limit_requests
    def _blockchain_data(self):
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

        return data

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
                                                                    utc=not config.get('USE_LOCALTIME'))

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
