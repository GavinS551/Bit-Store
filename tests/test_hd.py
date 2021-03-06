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

import pytest

from lib.core.hd import HDWallet, PublicHDWalletObjectError, InvalidPath


VALID_MNEMONIC = 'lion harvest elbow beauty butter spirit park jungle dose need flock hobby'
GAP_LIMIT = 1
PUBLIC_KEY = 'xpub661MyMwAqRbcFT711SemYJjjp83d3XnzDWeemB2wH1wSW7vjkxUaan6yDkDCam4HDEr8dDtG2b2XjkHKceEx52hfCmBG64cBk88ATr72oWa'

bip32_ = HDWallet.from_mnemonic(VALID_MNEMONIC, '0', gap_limit=GAP_LIMIT, segwit=False)
segwit_bip32_ = HDWallet.from_mnemonic(VALID_MNEMONIC, "49'/0'/0'", gap_limit=GAP_LIMIT, segwit=True)
public_bip32_ = HDWallet(PUBLIC_KEY, '0', gap_limit=GAP_LIMIT, segwit=False)

normal_addresses = bip32_.addresses()
segwit_addresses = segwit_bip32_.addresses()

normal_wif_keys = bip32_.wif_keys()
segwit_wif_keys = segwit_bip32_.wif_keys()

public_addresses = public_bip32_.addresses()


def test_public():
    assert not public_bip32_.is_private
    assert public_bip32_.addresses()[0] == normal_addresses[0]
    assert public_bip32_.wif_keys() is None

    with pytest.raises(PublicHDWalletObjectError):
        _ = HDWallet(key=PUBLIC_KEY, path="39'/0'/0'")


def test_is_private():
    assert bip32_.is_private
    assert segwit_bip32_.is_private


def test_constructor():
    with pytest.raises(InvalidPath):
        _ = HDWallet.from_mnemonic(VALID_MNEMONIC, path='222d')

    with pytest.raises(ValueError):
        _ = HDWallet.from_mnemonic(VALID_MNEMONIC, '0', gap_limit=-1)


def test_mnemonic_gen():
    assert HDWallet.check_mnemonic(HDWallet.gen_mnemonic())


def test_check_mnemonic():
    assert not HDWallet.check_mnemonic('NOT A MNEMONIC')
    assert HDWallet.check_mnemonic(VALID_MNEMONIC)


def test_check_path():
    assert HDWallet.check_path("0'")
    assert HDWallet.check_path("49'/0'/0'")
    assert not HDWallet.check_path('/')
    assert not HDWallet.check_path("O/0")
    assert not HDWallet.check_path("49''/0'/3")
    assert not HDWallet.check_path('')


def test_xkey_gen():
    assert bip32_.master_private_key == 'xprv9s21ZrQH143K2y2XuR7mBAo1G6D8e558rHj3xndKigQTdKbbDRAL2ynVNUwPLwHAk8wqH8peAMT5ujVTwzU9XdBsRyK8kshnUBAJTWCNqub'


def test_address_gen():
    assert normal_addresses[0][0] == '1E9emJj63vhNNzVLNDAHHbiTQgdF6dzG83'
    assert normal_addresses[1][0] == '1PphWYsNrphT3KMXntE4D5U896oYKyQbWp'

    assert segwit_addresses[0][0] == '3CcNeJbf3umiAJbWDQU7s444PATicEfxr8'
    assert segwit_addresses[1][0] == '33kxurPZvAZLeM7PYg5F2ekq6yS7DahrUe'


def test_wif_gen():
    assert normal_wif_keys[0][0] == 'L4XqkXusVoxrNH91cQrCDXbJLJ3ThvJXvecMAnzPfnL3pXPeSDt2'
    assert normal_wif_keys[1][0] == 'L5UPjSsf7VWhqFSbzWZKLEU1ymdPKCih2yHQATT73hKnTtS7NPiE'

    assert segwit_wif_keys[0][0] == 'KxQHThQo3t9HDSzZzYDYF58aEzqB7QbY2AMgGcCMcH4Krt8zrRRo'
    assert segwit_wif_keys[1][0] == 'KxfceVhP6DCvnyz2aN3ZCn4JJBTFsp7UzzVVReNZP78e7vwePkGx'


def test_address_wifkey_pairs():
    assert bip32_.address_wifkey_pairs() ==\
           {'receiving': dict(zip(normal_addresses[0], normal_wif_keys[0])),
            'change': dict(zip(normal_addresses[1], normal_wif_keys[1]))}
