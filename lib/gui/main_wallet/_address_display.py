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

from ...core import utils


class AddressDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master)

        self.main_wallet = main_wallet
        self.root = self.main_wallet.root

        self.tree_view = ttk.Treeview(self, columns=('Address', 'Balance', 'No. Txns'),
                                      selectmode='browse')

        self.tree_view.heading('#0', text='Type')
        self.tree_view.heading('#1', text='Address')
        self.tree_view.heading('#2', text=f'Balance ({self.main_wallet.display_units})')
        self.tree_view.heading('#3', text='No. Txns')

        self.tree_view.column('#0', minwidth=130, width=130)
        self.tree_view.column('#1', minwidth=400, width=400)
        self.tree_view.column('#2', minwidth=110, width=110)
        self.tree_view.column('#3', minwidth=100, width=100)

        self.tree_view.grid(row=0, column=0, sticky='nsew')

        # will prevent columns in the tree_view from bring re-sized
        def handle_click(event):
            if self.tree_view.identify_region(event.x, event.y) == "separator":
                return "break"
        self.tree_view.bind('<Button-1>', handle_click)

        self.scrollbar = ttk.Scrollbar(self, command=self.tree_view.yview)
        self.tree_view.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky='ns')

        self._last_wallet_transactions = None  # used to see if the display should be updated

        self._refresh_addresses()
        self._set_popup_event()

    def get_selected_address(self):
        try:
            sel = self.tree_view.selection()[0]
        except IndexError:
            # if nothing is selected
            return

        item = self.tree_view.item(sel)

        return item['values'][0]

    def _insert_row(self, *args):
        self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3]))

    def _populate_tree(self, addr_data):
        # delete all rows in the tree currently
        self.tree_view.delete(*self.tree_view.get_children())

        # addr_data should be a list of tuples for the 4 columns in tree view
        for a in addr_data:
            self._insert_row(*a)

    def _refresh_addresses(self):
        # only update if transactions have changed
        if self._last_wallet_transactions != self.root.btc_wallet.transactions:
            self._last_wallet_transactions = self.root.btc_wallet.transactions

            get_addr_type = self.root.btc_wallet.address_type
            wallet_units = self.main_wallet.to_wallet_units
            f2s = utils.float_to_str
            num_txns = self.root.btc_wallet.addr_num_transactions

            addr_bals = self.root.btc_wallet.address_balances

            # sorted showing addresses with balances first
            _r_addresses = self.root.btc_wallet.default_addresses['receiving']
            _r_addresses.sort(key=lambda x: sum(addr_bals[x]), reverse=True)

            _c_addresses = self.root.btc_wallet.default_addresses['change']
            _c_addresses.sort(key=lambda x: sum(addr_bals[x]), reverse=True)

            # then combine the two lists with both halves sorted
            addresses = _r_addresses + _c_addresses

            addr_data = [(get_addr_type(a), a, f2s(wallet_units(sum(addr_bals[a]), 'sat')),
                          num_txns(a)) for a in addresses]

            self._populate_tree(addr_data)

        self.root.after(self.main_wallet.refresh_data_rate, self._refresh_addresses)

    def _set_popup_event(self):
        def copy():
            self.main_wallet.root.clipboard_clear()
            item = self.tree_view.item(self.tree_view.selection()[0])['values'][0]  # first value is address
            self.main_wallet.root.clipboard_append(item)

        explorer_address = lambda: self.main_wallet.block_explorer.show_address(self.get_selected_address())
        qr_popup = lambda: self.main_wallet.root.qr_code_window(self, self.get_selected_address())

        popup = tk.Menu(self, tearoff=0)
        popup.add_command(label='Copy Address', command=copy)
        popup.add_command(label='Show QR code', command=qr_popup)
        popup.add_command(label='Open in block explorer', command=explorer_address)

        def do_popup(event):
            # get row under mouse
            iid = self.tree_view.identify_row(event.y)

            # if there was a row under mouse
            if iid:
                self.tree_view.selection_set(iid)
                self.tree_view.focus(iid)

                popup.tk_popup(event.x_root, event.y_root, 0)

        self.tree_view.bind('<Button-3>', do_popup)
