import tkinter as tk
from tkinter import ttk

from ...core import config, structs, utils


class _TransactionDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master)
        self.main_wallet = main_wallet

        self.tree_view = ttk.Treeview(self, columns=('Date', 'Amount', 'Fiat Amount', 'Balance', 'Fiat Balance')) \
            if config.GUI_SHOW_FIAT_TX_HISTORY else ttk.Treeview(self, columns=('Date', 'Amount', 'Balance'))

        # these headings and columns are always the same order/dimensions
        self.tree_view.heading('#0', text='Confirmations')
        self.tree_view.heading('#1', text='Date')
        self.tree_view.heading('#2', text=f'Amount ({self.main_wallet.display_units})')

        self.tree_view.column('#0', minwidth=100, width=100)
        self.tree_view.column('#2', minwidth=120, width=120)

        if config.GUI_SHOW_FIAT_TX_HISTORY:

            self.tree_view.heading('#3', text=f'({config.FIAT})')
            self.tree_view.heading('#4', text=f'Balance ({self.main_wallet.display_units})')
            self.tree_view.heading('#5', text=f'({config.FIAT})')

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

        self.scrollbar = ttk.Scrollbar(self, command=self.tree_view.yview)
        self.tree_view.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky='ns')

        self._cached_display_data = None
        self._refresh_transactions()

    def _insert_row(self, *args):
        if config.GUI_SHOW_FIAT_TX_HISTORY:
            self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3], args[4], args[5]))
        else:
            self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3]))

    def _populate_tree(self, *args):
        # delete all rows in the tree
        self.tree_view.delete(*self.tree_view.get_children())

        for arg in args:
            self._insert_row(*arg)

    def _refresh_transactions(self):

        # Transactions class will allow the sorting of txns by date,
        # and txns are stored as structs.TransactionData instances
        transactions = structs.Transactions.from_list(self.main_wallet.root.btc_wallet.transactions)
        sorted_txns = transactions.date_sorted_transactions(ascending=False)

        # satoshis will be divided by this number to get amount in terms of self.main_wallet.display_units
        f = self.main_wallet.unit_factor

        sat_to_btc = lambda sat: sat / config.UNIT_FACTORS['BTC']
        price = self.main_wallet.price.get()
        f2s = utils.float_to_str

        if config.GUI_SHOW_FIAT_TX_HISTORY:
            display_data = [[t.confirmations, t.date, f'{f2s(t.wallet_amount / f, show_plus_sign=True)}',
                             f2s(round(sat_to_btc(t.wallet_amount) * price, 2), show_plus_sign=True),
                             f'{f2s(transactions.balances[t] / f)}',
                             f2s(round(sat_to_btc(transactions.balances[t]) * price, 2))] for t in sorted_txns]
        else:
            display_data = [[t.confirmations, t.date, f'{f2s(t.wallet_amount / f, show_plus_sign=True)}',
                             f'{f2s(transactions.balances[t] / f)}'] for t in sorted_txns]

        # only refresh tree_view if data has changed
        if not self._cached_display_data == display_data:
            self._populate_tree(*display_data)

        self._cached_display_data = display_data

        self.main_wallet.root.after(self.main_wallet.refresh_data_rate, self._refresh_transactions)
