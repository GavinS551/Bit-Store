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

import tkinter as tk
from tkinter import ttk

from types import SimpleNamespace

from ...core import config, structs, utils


class TransactionDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master)
        self.main_wallet = main_wallet

        self.tree_view = ttk.Treeview(self, columns=('Date', 'Amount', 'Fiat Amount', 'Balance', 'Fiat Balance'),
                                      selectmode='browse') \
            if config.get_value('GUI_SHOW_FIAT_TX_HISTORY') \
            else ttk.Treeview(self, columns=('Date', 'Amount', 'Balance'), selectmode='browse')

        # these headings and columns are always the same order/dimensions
        self.tree_view.heading('#0', text='Confirmations')
        self.tree_view.heading('#1', text='Date')
        self.tree_view.heading('#2', text=f'Amount ({self.main_wallet.display_units})')

        self.tree_view.column('#0', minwidth=100, width=100)
        self.tree_view.column('#2', minwidth=120, width=120)

        if config.get_value('GUI_SHOW_FIAT_TX_HISTORY'):

            self.tree_view.heading('#3', text=f'({config.get_value("FIAT")})')
            self.tree_view.heading('#4', text=f'Balance ({self.main_wallet.display_units})')
            self.tree_view.heading('#5', text=f'({config.get_value("FIAT")})')

            self.tree_view.column('#1', minwidth=220, width=220)
            self.tree_view.column('#3', minwidth=90, width=90)
            self.tree_view.column('#4', minwidth=120, width=120)
            self.tree_view.column('#5', minwidth=90, width=90)

        else:

            self.tree_view.heading('#3', text=f'Balance ({self.main_wallet.display_units})')

            self.tree_view.column('#1', minwidth=400, width=400)
            self.tree_view.column('#3', minwidth=120, width=120)

        self.tree_view.grid(row=0, column=0, sticky='ns')

        # will prevent columns in the tree_view from bring re-sized
        def handle_click(event):
            if self.tree_view.identify_region(event.x, event.y) == "separator":
                return "break"
        self.tree_view.bind('<Button-1>', handle_click)

        self.tree_view.bind('<Double-1>', self._on_double_click)

        self.scrollbar = ttk.Scrollbar(self, command=self.tree_view.yview)
        self.tree_view.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky='ns')

        self._last_wallet_transactions = None  # used to see if the display should be updated

        self._refresh_transactions()
        self._set_popup_event()

    def get_selected_transaction(self):
        try:
            sel = self.tree_view.selection()[0]
        except IndexError:
            # if nothing is selected
            return

        item = self.tree_view.item(sel)
        txid = item['tags'][0]
        return structs.Transactions.from_list(self.main_wallet.root.btc_wallet.transactions).find_txn_by_id(txid)

    def _insert_row(self, *args, tags=None):
        if config.get_value('GUI_SHOW_FIAT_TX_HISTORY'):
            self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3], args[4], args[5]),
                                  tags=tags)
        else:
            self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3]), tags=tags)

    def _populate_tree(self, tx_data, tags):
        # delete all rows in the tree
        self.tree_view.delete(*self.tree_view.get_children())

        for tx, tag in zip(tx_data, tags):
            self._insert_row(*tx, tags=[tag])

    def _refresh_transactions(self):
        # only update if transactions have changed
        if self._last_wallet_transactions != self.main_wallet.root.btc_wallet.transactions:
            self._last_wallet_transactions = self.main_wallet.root.btc_wallet.transactions

            # Transactions class will allow the sorting of txns by date,
            # and txns are stored as structs.TransactionData instances
            transactions = structs.Transactions.from_list(self.main_wallet.root.btc_wallet.transactions)
            sorted_txns = transactions.date_sorted_transactions(ascending=False)

            # satoshis will be divided by this number to get amount in terms of self.main_wallet.display_units
            f = self.main_wallet.unit_factor

            sat_to_btc = lambda sat: sat / config.UNIT_FACTORS['BTC']
            price = self.main_wallet.price.get()
            f2s = utils.float_to_str
            wallet_units = self.main_wallet.to_wallet_units

            if config.get_value('GUI_SHOW_FIAT_TX_HISTORY'):
                display_data = [[t.confirmations, t.date, f2s(t.wallet_amount / f, show_plus_sign=True),
                                 f2s(round(sat_to_btc(t.wallet_amount) * price, 2), show_plus_sign=True, places=2),
                                 f2s(wallet_units(transactions.balances[t], 'sat')),
                                 f2s(sat_to_btc(transactions.balances[t]) * price, 2, places=2)] for t in sorted_txns]
            else:
                display_data = [[t.confirmations, t.date, f2s(t.wallet_amount / f, show_plus_sign=True),
                                 f2s(wallet_units(transactions.balances[t], 'sat'))] for t in sorted_txns]

            # tags containing txid corresponding to txn args in display_data
            tags = [t.txid for t in sorted_txns]

            self._populate_tree(display_data, tags)

        self.main_wallet.root.after(self.main_wallet.refresh_data_rate, self._refresh_transactions)

    def _set_popup_event(self):
        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label='Details',
                          command=lambda: self._on_double_click(SimpleNamespace(widget=self.tree_view)))

        def do_popup(event):
            # get row under mouse
            iid = self.tree_view.identify_row(event.y)

            # if there was a row under mouse
            if iid:
                self.tree_view.selection_set(iid)
                self.tree_view.focus(iid)

                popup.tk_popup(event.x_root, event.y_root, 0)

        self.tree_view.bind('<Button-3>', do_popup)

    def _on_double_click(self, event):
        txn = self.get_selected_transaction()

        # no selection in treeview
        if txn is None:
            return

        self.main_wallet.display_txn(txn)
