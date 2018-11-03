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

import sys
import contextlib
import os
import getpass

from ..core import wallet, data


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Error - Script Usage: "signtx.py <wallet_name> '
              '<wallet_password> <path/to/transaction/file>"\n'
              '(Use ! as a password and you will be prompted '
              'for a password)')
        exit(-1)

    w_name = sys.argv[1]
    w_pass = sys.argv[2]
    tx_path = sys.argv[3]

    if w_pass == '!':
        w_pass = getpass.getpass()

    print('Loading wallet...')

    try:
        w = wallet.get_wallet(w_name, w_pass, offline=True)

    except data.IncorrectPasswordError:
        print('Error: Incorrect wallet password')
        exit(-1)

    except wallet.WalletNotFoundError:
        print(f'Error: Wallet "{w_name}" does not exist')
        exit(-1)

    if w.get_metadata(w.name)['watch_only']:
        print('Error: Cannot sign a transaction with a watch-only wallet')
        exit(-1)

    print('Wallet loaded')

    try:
        txn = w.file_import_transaction(tx_path)
        print('Transaction successfully imported')

    except wallet.TransactionImportError as ex:
        print(ex)
        exit(-1)

    if txn.is_signed:
        print('Error: Transaction is already signed')
        exit(-1)

    print('Signing transaction...')
    w.sign_transaction(txn, w_pass)
    print('Transaction signed')

    with contextlib.suppress(OSError):
        os.remove(tx_path)
        print('Unsigned transaction deleted')

    print('Exporting signed transaction')

    parent_dir = os.path.abspath(os.path.dirname(tx_path))
    signed_path = os.path.join(parent_dir, 'signed.txn')
    w.file_export_transaction(signed_path, txn)

    print(f'Signed transaction sucessfully exported to {signed_path}')
