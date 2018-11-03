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

""" data structures that make handling wallet data simpler """

from typing import NamedTuple
from datetime import datetime
import functools

from . import config


class UTXOData(NamedTuple):
    """ NamedTuple that makes handling utxo data in standard format easier """
    txid: str
    output_num: int
    address: str
    script: str
    value: int
    confirmations: int

    def is_confirmed(self):
        return self.confirmations > 0

    @property
    def standard_format(self):
        """ returns data in standard format """
        return [self.txid, self.output_num, self.address, self.script, self.value, self.confirmations]


class TransactionData(NamedTuple):
    """ NamedTuple for handling transactions in standard format """
    txid: str
    date: str
    block_height: int
    confirmations: int
    fee: int
    vsize: int
    inputs: list
    outputs: list
    wallet_amount: int

    def __eq__(self, other):
        return self.txid == other.txid

    def __hash__(self):
        """ named tuple's default hash has to be overridden as inputs and
         outputs lists are un-hashable
         """
        return hash(self.txid)


class Transactions:
    """ methods that will usually be called in a loop many times are cached """

    @classmethod
    def from_list(cls, txn_list):
        """ returns a Transactions class from a list of dicts (format they are stored in) """
        return cls(transactions=[TransactionData(**t) for t in txn_list])

    def __init__(self, transactions):
        # list of TransactionData named tuples
        self._transactions = transactions

    @functools.lru_cache(maxsize=None)
    def date_sorted_transactions(self, ascending=True):
        """ returns self.transactions sorted by date """
        def _date_sort_key(txn):
            return datetime.strptime(txn.date, config.DATETIME_FORMAT)

        # sorting transactions by ascending txn date
        sorted_transactions = sorted(self._transactions, key=_date_sort_key,
                                     reverse=not ascending)

        return sorted_transactions

    @property
    @functools.lru_cache(maxsize=None)
    def balances(self):
        """ dict of txns and the balance of the wallet at that particular txn """
        balances_dict = dict.fromkeys([txn for txn in self._transactions], 0)

        running_total = 0
        # using date sorted transactions as the oldest chronological txn
        # will be the first change (+) in the wallet balance
        for txn in self.date_sorted_transactions():
            running_total += txn.wallet_amount
            balances_dict[txn] = running_total

        return balances_dict

    def find_address_with_txns(self, address_list):
        """ returns addresses from address_list arg in that are associated
        with at least one transaction in self._transactions
        """
        # addresses shouldn't be repeated if they are associated with more than
        # one transaction
        addresses = set()

        for t in self._transactions:
            for i in t.inputs:
                if i['address'] in address_list:
                    addresses.add(i['address'])

            for o in t.outputs:
                if o['address'] in address_list:
                    addresses.add(o['address'])

        return addresses

    def find_txn_by_id(self, txid):
        for t in self._transactions:
            if t.txid == txid:
                return t
        else:
            return None
