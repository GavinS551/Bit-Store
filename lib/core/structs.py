from dataclasses import dataclass
from datetime import datetime

from . import config


@dataclass
class UTXOData:
    """ dataclass that makes handling utxo data in standard format easier """
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

    def __eq__(self, other):
        return self.txid == other.txid and self.output_num == other.output_num

    def __hash__(self):
        return hash((self.txid, self.output_num))


@dataclass
class TransactionData:
    """ dataclass for handling transactions in standard format """

    txid: str
    date: str
    block_height: int
    confirmations: int
    fee: int
    size: int
    inputs: list
    outputs: list
    wallet_amount: int

    @property
    def standard_format(self):
        """ returns data in standard format """
        return {
            'txid': self.txid,
            'date': self.date,
            'block_height': self.block_height,
            'confirmations': self.confirmations,
            'fee': self.fee,
            'size': self.size,
            'inputs': self.inputs,
            'outputs': self.outputs,
            'wallet_amount': self.wallet_amount
        }

    def __eq__(self, other):
        return self.txid == other.txid

    def __hash__(self):
        return hash(self.txid)


class Transactions:

    def __init__(self, transactions):

        # list of TransactionData dataclasses
        self.transactions = transactions

    @property
    def date_sorted_transactions(self):
        """ returns self.transactions sorted by date """

        def _date_sort_key(txn):
            return datetime.strptime(txn.date, config.DATETIME_FORMAT)

        # sorting transactions by ascending txn date
        sorted_transactions = sorted(self.transactions, key=_date_sort_key)

        return sorted_transactions

    @property
    def balances(self):
        """ dict of txns and the balance of the wallet at that particular txn """

        balances_dict = dict.fromkeys([txn for txn in self.transactions], 0)

        running_total = 0
        for txn in self.date_sorted_transactions:
            running_total += txn.wallet_amount
            balances_dict[txn] = running_total

        return balances_dict
