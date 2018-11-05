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

from . import config


def explorer_api(source):
    # tuple of urls should have txid url and address url
    sources = {
        'blockchain.info': ('https://www.blockchain.com/btc/tx/', 'https://www.blockchain.com/btc/address/'),
        'blockcypher.com': ('https://live.blockcypher.com/btc/tx/', 'https://live.blockcypher.com/btc/address/'),
        'blockchair.com': ('https://blockchair.com/bitcoin/transaction/', 'https://blockchair.com/bitcoin/address/')
    }
    # ensure all sources in config are implemented
    assert all(s in config.POSSIBLE_EXPLORER_SOURCES for s in sources)

    if source not in sources:
        raise NotImplementedError(f'"{source}" is not an implemented explorer api')

    return BlockExplorer(sources[source][0], sources[source][1])


class BlockExplorer:
    """ class that can open different block explorers in web browser to
    show transaction/address info
    """
    def __init__(self, tx_url, addr_url):
        self.tx_url = tx_url
        self.addr_url = addr_url

    def show_transaction(self, txid):
        webbrowser.open(self.tx_url + txid)

    def show_address(self, address):
        webbrowser.open(self.addr_url + address)
