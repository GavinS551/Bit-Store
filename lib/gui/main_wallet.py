import tkinter as tk
from tkinter import ttk

import threading
import time
import string

from ..core import structs, config


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.refresh_data_rate = 3

        self.display_units = config.UNITS
        self.unit_factor = config.UNIT_FACTORS[self.display_units]


        # attributes below will be updated in _refresh_data method
        self.wallet_balance = tk.IntVar()
        self.unconfirmed_wallet_balance = tk.IntVar()
        self.price = tk.IntVar()
        self.fiat_wallet_balance = tk.IntVar()
        self.unconfirmed_fiat_wallet_balance = tk.IntVar()

    def gui_draw(self):

        title_label = ttk.Label(self, text=self.root.btc_wallet.name,
                                font=self.root.bold_title_font)
        title_label.grid(row=0, column=0)

        notebook = ttk.Notebook(self)

        tx_display = _TransactionDisplay(notebook, self)
        tx_display.grid()
        notebook.add(tx_display, text='Transactions')

        send_display = _SendDisplay(notebook, self)
        send_display.grid()
        notebook.add(send_display, text='Send')

        notebook.grid(row=1, column=0, pady=10)

        self._draw_bottom_info_bar()
        refresh_thread = threading.Thread(target=self._refresh_data,
                                          name='GUI_MAIN_WALLET_REFRESH_THREAD',
                                          daemon=True)
        refresh_thread.start()

    def _draw_bottom_info_bar(self):
        bottom_info_frame = ttk.Frame(self)

        balance_frame = ttk.Frame(bottom_info_frame)
        balance_label = ttk.Label(balance_frame, text='Wallet Balance:',
                                  font=self.root.tiny_font)
        balance = ttk.Label(balance_frame, textvariable=self.wallet_balance,
                            font=self.root.tiny_font + ('bold',))
        balance_units = ttk.Label(balance_frame, text=f'{self.display_units}',
                                  font=self.root.tiny_font + ('bold',))

        plus_label = ttk.Label(balance_frame, text='+', font=self.root.tiny_font)
        unconfirmed_balance = ttk.Label(balance_frame, textvariable=self.unconfirmed_wallet_balance,
                                        font=self.root.tiny_font)
        unconfirmed_balance_text = ttk.Label(balance_frame, text='unconfirmed',
                                             font=self.root.tiny_font)

        balance_label.grid(row=0, column=0)
        balance.grid(row=0, column=1)
        balance_units.grid(row=0, column=2)

        plus_label.grid(row=0, column=3)
        unconfirmed_balance.grid(row=0, column=4)
        unconfirmed_balance_text.grid(row=0, column=5)

        balance_frame.grid(row=0, column=0, sticky='s')

        fiat_balance_frame = ttk.Frame(bottom_info_frame)
        fiat_balance_label = ttk.Label(fiat_balance_frame, text=f'{config.FIAT} Balance:',
                                       font=self.root.tiny_font)
        fiat_balance = ttk.Label(fiat_balance_frame, textvariable=self.fiat_wallet_balance,
                                 font=self.root.tiny_font + ('bold',))

        fiat_plus_label = ttk.Label(fiat_balance_frame, text='+', font=self.root.tiny_font)
        fiat_unconfirmed_balance = ttk.Label(fiat_balance_frame,
                                             textvariable=self.unconfirmed_fiat_wallet_balance,
                                             font=self.root.tiny_font)
        fiat_unconfirmed_label = ttk.Label(fiat_balance_frame, text='unconfirmed',
                                           font=self.root.tiny_font)

        fiat_balance_label.grid(row=0, column=0)
        fiat_balance.grid(row=0, column=1)

        fiat_plus_label.grid(row=0, column=2)
        fiat_unconfirmed_balance.grid(row=0, column=3)
        fiat_unconfirmed_label.grid(row=0, column=4)

        fiat_balance_frame.grid(row=1, column=0, sticky='s')

        bottom_info_frame.grid()

    def _refresh_data(self):
        while True:
            self.wallet_balance.set(self.root.btc_wallet.wallet_balance / self.unit_factor)
            self.unconfirmed_wallet_balance.set(self.root.btc_wallet.unconfirmed_wallet_balance / self.unit_factor)
            self.price.set(self.root.btc_wallet.price)
            self.fiat_wallet_balance.set(self.root.btc_wallet.fiat_wallet_balance)
            self.unconfirmed_fiat_wallet_balance.set(self.root.btc_wallet.unconfirmed_fiat_wallet_balance)

            time.sleep(self.refresh_data_rate)


class _TransactionDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master)
        self.main_wallet = main_wallet

        self.tree_view = ttk.Treeview(self, columns=('Date', 'Amount', 'Balance'))
        self.tree_view.heading('#0', text='Confirmations')
        self.tree_view.heading('#1', text='Date')
        self.tree_view.heading('#2', text=f'Amount ({self.main_wallet.display_units})')
        self.tree_view.heading('#3', text=f'Balance ({self.main_wallet.display_units})')

        self.tree_view.column('#0', stretch=False, minwidth=100, width=100)
        self.tree_view.column('#1', stretch=False, minwidth=400, width=400)
        self.tree_view.column('#2', stretch=False, minwidth=120, width=120)
        self.tree_view.column('#3', stretch=False, minwidth=120, width=120)

        self.tree_view.grid(row=0, column=0)

        self.scrollbar = ttk.Scrollbar(self, command=self.tree_view.yview)
        self.tree_view.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky='ns')

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
                                                 for txn in self.main_wallet.root.btc_wallet.transactions])

            # satoshis will be divided by this number to get amount in terms of self.main_wallet.display_units
            f = self.main_wallet.unit_factor

            # list reversed so the newest txn will be inserted first in tree_view
            display_data = [[t.confirmations, t.date,
                            f'{t.wallet_amount / f:+}', f'{transactions.balances[t] / f}']
                            for t in transactions.balances]

            # only refresh tree_view if data has changed
            if not self._cached_display_data == display_data:
                self._populate_tree(*display_data)

            self._cached_display_data = display_data

            time.sleep(self.main_wallet.refresh_data_rate)


class _SendDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master)
        self.main_wallet = main_wallet

        # used for validation in amount entry widgets
        validate = (self.main_wallet.root.register(self._entry_int_validate), '%S', '%P', '%s')

        self.address_label = ttk.Label(self, text='Pay To:',
                                       font=self.main_wallet.root.small_font,)
        self.address_label.grid(row=0, column=0, pady=10, padx=10, sticky='e')

        self.address_entry = ttk.Entry(self, width=70)
        self.address_entry.grid(row=0, column=1, pady=10, padx=20, columnspan=3)

        self.amount_btc_label = ttk.Label(self, text=f'Amount ({self.main_wallet.display_units}):',
                                      font=self.main_wallet.root.small_font)
        self.amount_btc_label.grid(row=1, column=0, pady=10, padx=10, sticky='e')

        self.amount_btc_entry = ttk.Entry(self, validate='key', validatecommand=validate)
        self.amount_btc_entry.bind('<KeyRelease>', self._amount_btc_entry_to_fiat)
        self.amount_btc_entry.grid(row=1, column=1, pady=10, padx=20, sticky='w')

        self.amount_fiat_label = ttk.Label(self, text=f'Amount ({config.FIAT}):',
                                      font=self.main_wallet.root.small_font)
        self.amount_fiat_label.grid(row=1, column=2, pady=10, padx=10, sticky='w')

        self.amount_fiat_var = tk.IntVar()
        self.amount_fiat = ttk.Label(self, textvariable=self.amount_fiat_var)
        self.amount_fiat.grid(row=1, column=3, pady=10, padx=10, sticky='w')

        self.fee_label = ttk.Label(self, text='Fee (sat/byte):',
                                   font=self.main_wallet.root.small_font)
        self.fee_label.grid(row=2, column=0, pady=10, padx=10, sticky='e')

        self.fee_entry = ttk.Entry(self)
        self.fee_entry.grid(row=2, column=1, pady=10, padx=20, sticky='w')

        self.total_cost_label = ttk.Label(self, text='Total Cost:',
                                          font=self.main_wallet.root.small_font)
        self.total_cost_label.grid(row=3, column=0, pady=10, padx=10, sticky='e')

        self.submit_button = ttk.Button(self, text='Submit')
        self.submit_button.grid(row=4, column=0)

    def _entry_int_validate(self, char, entry, before_change):
        """ validates that anything entered in amount entries are valid numbers """
        units_max_decimal_places = {
            'BTC': 8,
            'mBTC': 5,
            'bits': 2,
            'sat': 0
        }

        if char in string.digits + '.' and not entry.count('.') > 1:
            if entry.count('.') == 1 and self.main_wallet.display_units != 'sat':
                if len(entry.split('.')[1]) <= units_max_decimal_places[self.main_wallet.display_units]:
                    return True
                else:
                    return False

            # satoshi units are not divisible
            elif entry.count('.') == 1 and self.main_wallet.display_units == 'sat':
                return False

            else:
                return True

        # for deleting the whole, or part of, the entry
        elif not entry or entry in before_change:
            return True

        else:
            return False

    def _amount_btc_entry_to_fiat(self, event):

        # empty string resets fiat amount
        if not event.widget.get():
            self.amount_fiat_var.set(0)
            return 

        value = float(event.widget.get())

        # convert different units into btc, as price is in terms of btc
        def to_btc(units, amount):
            if units == 'BTC':
                return amount
            else:
                btc = (amount * config.UNIT_FACTORS[units]) / config.UNIT_FACTORS['BTC']
                return btc

        fiat_amount = round(self.main_wallet.price.get() * to_btc(self.main_wallet.display_units, value), 2)

        self.amount_fiat_var.set(fiat_amount)
