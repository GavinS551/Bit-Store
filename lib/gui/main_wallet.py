import tkinter as tk
from tkinter import ttk

import threading
import time

from ..core import structs


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        # attributes defined in gui_draw
        self.tx_display = None

    def gui_draw(self):
        title_label = ttk.Label(self, text=self.root.btc_wallet.name,
                                font=self.root.bold_title_font)
        title_label.grid(row=0, column=0)

        notebook = ttk.Notebook(self)

        self.tx_display = _TransactionDisplay(notebook, self.root)

        self.tx_display.grid()
        notebook.add(self.tx_display, text='Transactions')

        button_frame = ttk.Frame(notebook)
        button = ttk.Button(button_frame, text='ADD TX')
        button.grid()
        button_frame.grid()
        notebook.add(button_frame, text='TEST')

        notebook.grid(row=1, column=0)

class _TransactionDisplay(ttk.Frame):

    def __init__(self, master, root):
        ttk.Frame.__init__(self, master)
        self.root = root

        self.tree_view = ttk.Treeview(self, columns=('Date', 'Amount', 'Balance'))
        self.tree_view.heading('#0', text='Confirmations')
        self.tree_view.heading('#1', text='Date')
        self.tree_view.heading('#2', text='Amount')
        self.tree_view.heading('#3', text='Balance')

        self.tree_view.column('#0', stretch=True, width=100)
        self.tree_view.column('#1', stretch=True, width=400)
        self.tree_view.column('#2', stretch=True, width=100)
        self.tree_view.column('#3', stretch=True, width=100)

        self.tree_view.pack()

        self._cached_display_data = None

        self.refresh_thread = threading.Thread(target=self._refresh_transactions,
                                               name='GUI_TRANSACTION_DISPLAY_UPDATER',
                                               daemon=True)
        self.refresh_thread.start()

    def _insert_row(self, *args):
        self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3]))

    def _populate_tree(self, *args):
        # delete all rows in the tree
        self.tree_view.delete(*self.tree_view.get_children())

        for arg in args:
            self._insert_row(*arg)

    def _refresh_transactions(self):
        while True:
            # list of TransactionData dataclasses made from standard format transactions
            transactions = structs.Transactions([structs.TransactionData(**txn)
                                                        for txn in self.root.btc_wallet.transactions])

            # list reversed so the newest txn will be inserted first in tree_view
            display_data = [[t.confirmations, t.date, f'{t.wallet_amount:+d}', transactions.balances[t]]
                            for t in transactions.balances]

            # only refresh tree_view if data has changed
            if not self._cached_display_data == display_data:
                self._populate_tree(*display_data)

            self._cached_display_data = display_data

            time.sleep(3)
