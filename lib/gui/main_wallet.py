import tkinter as tk
from tkinter import ttk

import time
import string
from threading import Event

from ..core import structs, config, utils, tx


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.refresh_data_rate = 3000  # milliseconds

        self.display_units = config.UNITS
        self.unit_factor = config.UNIT_FACTORS[self.display_units]
        self.max_decimal_places = config.UNITS_MAX_DECIMAL_PLACES[self.display_units]

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
        tx_display.grid(sticky='nsew')
        notebook.add(tx_display, text='Transactions')

        send_display = _SendDisplay(notebook, self)
        send_display.grid(sticky='nsew')
        notebook.add(send_display, text='Send')

        notebook.grid(row=1, column=0, pady=10)

        self._draw_bottom_info_bar()
        self._refresh_data()

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

        self.wallet_balance.set(self.root.btc_wallet.wallet_balance / self.unit_factor)
        self.unconfirmed_wallet_balance.set(self.root.btc_wallet.unconfirmed_wallet_balance / self.unit_factor)
        self.price.set(self.root.btc_wallet.price)
        self.fiat_wallet_balance.set(self.root.btc_wallet.fiat_wallet_balance)
        self.unconfirmed_fiat_wallet_balance.set(self.root.btc_wallet.unconfirmed_fiat_wallet_balance)

        self.root.after(self.refresh_data_rate, self._refresh_data)


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
        self._refresh_transactions()

    def _insert_row(self, *args):
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
        sorted_txns = transactions.date_sorted_transactions()


        # satoshis will be divided by this number to get amount in terms of self.main_wallet.display_units
        f = self.main_wallet.unit_factor

        display_data = [[t.confirmations, t.date,
                        f'{t.wallet_amount / f:+}', f'{transactions.balances[t] / f}']
                        for t in sorted_txns]

        # only refresh tree_view if data has changed
        if not self._cached_display_data == display_data:
            self._populate_tree(*display_data)

        self._cached_display_data = display_data

        self.main_wallet.root.after(self.main_wallet.refresh_data_rate, self._refresh_transactions)


class _SendDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master, padding=5)
        self.main_wallet = main_wallet

        self.btc_wallet = self.main_wallet.root.btc_wallet
        self.transaction = None  # initial transaction will be created with 0 fee
        self.amount_over_balance = False

        self._make_transaction_thread_event = Event()
        # used to prevent 2 _make_transaction threads from running at same time
        self._thread_running = False

        # used for input validation in entry widgets
        address_validate = (self.main_wallet.root.register(self._address_entry_validate), '%P')
        amount_validate = (self.main_wallet.root.register(self._entry_btc_amount_validate), '%S', '%P', '%s')
        fee_validate = (self.main_wallet.root.register(self._entry_btc_amount_validate), '%S', '%P', '%s', True)

        address_label = ttk.Label(self, text='Pay To:',
                                  font=self.main_wallet.root.small_font)
        address_label.grid(row=0, column=0, pady=5, padx=10, sticky='e')

        self.address_entry = ttk.Entry(self, width=70, validate='key', validatecommand=address_validate)
        self.address_entry.grid(row=0, column=1, pady=5, padx=20, columnspan=3)

        amount_btc_label = ttk.Label(self, text=f'Amount ({self.main_wallet.display_units}):',
                                     font=self.main_wallet.root.small_font)
        amount_btc_label.grid(row=1, column=0, pady=5, padx=10, sticky='e')

        amount_frame = ttk.Frame(self)

        self.amount_btc_entry = ttk.Entry(amount_frame, validate='key', validatecommand=amount_validate)
        self.amount_btc_entry.bind('<KeyRelease>', self.on_btc_amount_key_press)
        self.amount_btc_entry['state'] = tk.DISABLED  # enabled after address entry
        self.amount_btc_entry.grid(row=0, column=0, pady=5)

        amount_fiat_label = ttk.Label(amount_frame, text=f'Amount ({config.FIAT}):',
                                      font=self.main_wallet.root.small_font)
        amount_fiat_label.grid(row=0, column=1, pady=5, padx=20, sticky='w')

        self.amount_fiat_var = tk.StringVar(value='0')
        self.amount_fiat = ttk.Label(amount_frame, textvariable=self.amount_fiat_var,
                                     font=self.main_wallet.root.small_font, width=15)
        self.amount_fiat.grid(row=0, column=2, pady=5, sticky='w')

        amount_frame.grid(row=1, column=1, pady=5, padx=20, sticky='w')

        fee_label = ttk.Label(self, text='Fee (sat/byte):',
                              font=self.main_wallet.root.small_font)
        fee_label.grid(row=2, column=0, pady=5, padx=10, sticky='e')

        fee_frame = ttk.Frame(self)

        self.fee_entry = ttk.Entry(fee_frame, validate='key', validatecommand=fee_validate)
        self.fee_entry.bind('<KeyRelease>', lambda _: self.on_fee_key_press())  # event arg is ignored for now
        self.fee_entry['state'] = tk.DISABLED # enabled after address entry
        self.fee_entry.grid(row=0, column=0, pady=5, padx=20, sticky='w')

        self.size_label_var = tk.IntVar(value=0)
        self.fee0 = ttk.Label(fee_frame, text='x', font=self.main_wallet.root.small_font)
        self.fee0.grid(row=0, column=1)

        self.fee1 = ttk.Label(fee_frame, textvariable=self.size_label_var,
                              font=self.main_wallet.root.small_font)
        self.fee1.grid(row=0, column=2)

        self.fee2 = ttk.Label(fee_frame, text='bytes = ', font=self.main_wallet.root.small_font)
        self.fee2.grid(row=0, column=3)

        # total fee in main_wallet.display_units (sat per bytes * txn size)
        self.total_fee_var = tk.StringVar(value='0')
        self.total_fee = ttk.Label(fee_frame, textvariable=self.total_fee_var,
                                   font=self.main_wallet.root.small_font, width=15)
        self.total_fee.grid(row=0, column=4, padx=25, sticky='w')

        # if tx size is less than 3 digits, labels will be hidden,
        # as that indicates that an amount of 0 is currently entered
        self.fee_labels_hidden = False
        self.hide_fee_labels()

        fee_frame.grid(row=2, column=1, sticky='w')

        total_cost_label = ttk.Label(self, text=f'Total ({self.main_wallet.display_units}):',
                                     font=self.main_wallet.root.small_font)
        total_cost_label.grid(row=3, column=0, pady=5, padx=10, sticky='e')

        total_cost_frame = ttk.Frame(self)

        self.total_cost_var = tk.StringVar(value='0')
        self.total_cost = ttk.Label(total_cost_frame, textvariable=self.total_cost_var,
                                    font=self.main_wallet.root.small_font, width=15)
        self.total_cost.grid(row=0, column=0, pady=5, padx=21, sticky='w')

        total_fiat_cost_label = ttk.Label(total_cost_frame, text=f'Total ({config.FIAT}):',
                                          font=self.main_wallet.root.small_font)
        total_fiat_cost_label.grid(row=0, column=2, sticky='w')

        self.total_fiat_cost_var = tk.StringVar(value='0')
        self.total_fiat_cost = ttk.Label(total_cost_frame, textvariable=self.total_fiat_cost_var,
                                    font=self.main_wallet.root.small_font, width=15)
        self.total_fiat_cost.grid(row=0, column=3, padx=36, sticky='w')

        total_cost_frame.grid(row=3, column=1, pady=5, sticky='w')

        send_button = ttk.Button(self, text='Send', command=self.on_send)
        send_button.grid(row=4, column=0, pady=20, padx=10, sticky='e')

        clear_button = ttk.Button(self, text='Clear', command=self.on_clear)
        clear_button.grid(row=4, column=1, pady=20, padx=10, sticky='w')

    def sign_transaction_window(self):
        pass

    def on_send(self):
        password = self.main_wallet.root.password_prompt()

    def on_clear(self):
        self._make_transaction_thread_event.set()
        self._thread_running = False

        self.amount_btc_entry.delete(0, tk.END)
        self.fee_entry.delete(0, tk.END)
        self.fee_entry['state'] = tk.DISABLED
        self.amount_btc_entry['state'] = tk.DISABLED

        self.address_entry['state'] = tk.NORMAL
        self.address_entry.delete(0, tk.END)

        self.hide_fee_labels()

    def to_satoshis(self, amount):
        """ converts amount (in terms of self.main_wallet.display_units) into satoshis"""
        return int(round(amount * self.main_wallet.unit_factor))

    def to_btc(self, amount):
        """ converts different units into btc, (needed as price is in terms of btc) """
        if self.main_wallet.display_units == 'BTC':
            return amount
        else:
            btc = self.to_satoshis(amount) / config.UNIT_FACTORS['BTC']
            return btc

    def to_fiat(self, amount):
        """ converts amount (display units) into fiat value """
        fiat_amount = round(self.main_wallet.price.get() * self.to_btc(amount), 2)
        return fiat_amount

    def hide_fee_labels(self):
        self.fee0.grid_remove()
        self.fee1.grid_remove()
        self.fee2.grid_remove()
        self.total_fee.grid_remove()

        self.fee_labels_hidden = True

    def show_fee_labels(self):
        self.fee0.grid()
        self.fee1.grid()
        self.fee2.grid()
        self.total_fee.grid()

        self.fee_labels_hidden = False

    def _validate_entries(self):

        if self.amount_over_balance:
            raise tx.InsufficientFundsError('You do not have enough funds')

        if not utils.validate_address(self.address_entry.get()):
            raise ValueError('Invalid address entered')

    def _address_entry_validate(self, entry):
        if utils.validate_address(entry):
            self.address_entry['state'] = tk.DISABLED

            if not self._thread_running:
                self._make_transaction_thread_event.clear()
                self._make_transaction()
                self._thread_running = True

            self.fee_entry['state'] = tk.NORMAL
            self.amount_btc_entry['state'] = tk.NORMAL
        else:
            self.fee_entry.delete(0, tk.END)
            self.amount_btc_entry.delete(0, tk.END)
            self.amount_fiat_var.set('0')
            self.total_cost_var.set('0')

            self.fee_entry['state'] = tk.DISABLED
            self.amount_btc_entry['state'] = tk.DISABLED
        return True

    def _entry_btc_amount_validate(self, char, entry, before_change, force_satoshis=False):
        """ validates that anything entered in amount entries are valid numbers """

        units = self.main_wallet.display_units if not force_satoshis else 'sat'
        max_decimal = self.main_wallet.max_decimal_places if not force_satoshis else 0

        if char in string.digits + '.' and not entry.count('.') > 1 and not entry == '.':

            if entry.count('.') == 1 and units != 'sat':
                if len(entry.split('.')[1]) <= max_decimal:
                    return True
                else:
                    return False

            # satoshi units are not divisible
            elif entry.count('.') == 1 and units == 'sat':
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
            self.amount_fiat_var.set('0')
            return 

        value = float(event.widget.get())
        fiat_amount = self.to_fiat(value)

        self.amount_fiat_var.set(utils.float_to_str(fiat_amount))

    def _totals_set(self):
        amount, fee = 0, 0

        if self.amount_btc_entry.get():
            amount = float(self.amount_btc_entry.get())

        if self.fee_entry.get():
            sat_byte = int(self.fee_entry.get())

            # fee is in satoshis so needs to be divided by unit factor
            fee = (sat_byte * self.transaction.estimated_size()) / self.main_wallet.unit_factor

        if self.to_satoshis(amount) < 1:
            self.hide_fee_labels()
        else:
            if self.fee_labels_hidden:
                self.show_fee_labels()

        self.size_label_var.set(self.transaction.estimated_size())
        self.total_fee_var.set(
            utils.float_to_str(round(fee, self.main_wallet.max_decimal_places)))
        self.total_cost_var.set(utils.float_to_str(round(amount + fee, self.main_wallet.max_decimal_places)))

    @utils.threaded(daemon=True)
    def _make_transaction(self):
        """ this method should be started before first key press on amount entries,
        so a size will be calculated already for fee
        """

        # to ensure only one thread is run at the same time
        if self._thread_running:
            return

        # key = tuple of amounts  value = transaction
        cached_txns = {}

        def set_amounts_colour(colour):
            self.total_cost.config(foreground=colour)
            self.amount_fiat.config(foreground=colour)

        while not self._make_transaction_thread_event.is_set():
            time.sleep(0.1)

            address = self.address_entry.get()

            if self.amount_btc_entry.get():
                amount = self.to_satoshis(float(self.amount_btc_entry.get()))
            else:
                amount = 0

            if self.fee_entry.get():
                fee = int(self.fee_entry.get()) * self.transaction.estimated_size()
            else:
                fee = 0

            # only recreate transaction if values are different
            if (amount, fee) in cached_txns:
                set_amounts_colour('black')
                self.amount_over_balance = False

                self.transaction = cached_txns[(amount, fee)]

            else:

                try:
                    transaction = self.btc_wallet.make_unsigned_transaction(
                        outs_amounts={address: amount},
                        fee=fee
                    )

                    cached_txns[(amount, fee)] = transaction
                    self.transaction = transaction
                    set_amounts_colour('black')
                    self.amount_over_balance = False

                except tx.InsufficientFundsError:
                    set_amounts_colour('red')
                    self.amount_over_balance = True

    def on_btc_amount_key_press(self, event):
        self._amount_btc_entry_to_fiat(event)
        self._totals_set()

    def on_fee_key_press(self):
        self._totals_set()
