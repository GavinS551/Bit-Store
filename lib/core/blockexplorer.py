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

import webbrowser


def explorer_api(source):
    sources = {
        'blockchain.info': BlockchainInfo,
    }

    if source.lower() not in sources:
        raise NotImplementedError(f'"{source}" is not an implemented explorer api')

    return sources[source]()


class _BlockExplorerBaseClass:
    """ class that can open different block explorers in web browser to
    show transaction/address info
    """
    bech32_support = None

    def show_transaction(self, txid):
        raise NotImplementedError

    def show_address(self, address):
        raise NotImplementedError


class BlockchainInfo(_BlockExplorerBaseClass):
    bech32_support = False

    def show_transaction(self, txid):
        url = f'https://www.blockchain.com/btc/tx/{txid}'
        webbrowser.open(url)

    def show_address(self, address):
        url = f'https://www.blockchain.com/btc/address/{address}'
        webbrowser.open(url)


class BlockCypher(_BlockExplorerBaseClass):
    bech32_support = False

    def show_transaction(self, txid):
        url = f'https://live.blockcypher.com/btc/tx/{txid}'
        webbrowser.open(url)

    def show_address(self, address):
        url = f'https://live.blockcypher.com/btc/address/{address}'
        webbrowser.open(url)


class Blockchair(_BlockExplorerBaseClass):

    def show_transaction(self, txid):
        url = f'https://blockchair.com/bitcoin/transaction/{txid}'
        webbrowser.open(url)

    def show_address(self, address):
        url = f'https://blockchair.com/bitcoin/address/{address}'
        webbrowser.open(url)
