from lib.core import blockchain
from ._blockchain_test_vectors import *


class TestBlockchainBaseClass(blockchain._BlockchainBaseClass):

    __test__ = False

    @property
    def transactions(self):
        return TRANSACTIONS


test_blockchain_obj = TestBlockchainBaseClass(addresses=ADDRESSES, refresh_rate=0, url='')


def test_utxo_gen():
    assert test_blockchain_obj.unspent_outputs == UTXOS


def test_address_balances_gen():
    assert test_blockchain_obj.address_balances == ADDRESS_BALANCES


def test_wallet_balance_gen():
    assert test_blockchain_obj.wallet_balance == WALLET_BALANCE


class TestBlockchainInfo(blockchain.BlockchainInfo):

    __test__ = False

    @property
    def _blockchain_data(self):
        return RAW_API_DATA


def test_blockchain_info_tx_gen():
    blockchain_info = TestBlockchainInfo(addresses=ADDRESSES, refresh_rate=0, url='')
    assert blockchain_info.transactions == TRANSACTIONS
