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
