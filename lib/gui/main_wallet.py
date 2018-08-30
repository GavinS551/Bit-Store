import tkinter as tk
from tkinter import ttk, messagebox

import time
import string
from threading import Event

import qrcode
from PIL import ImageTk

from ..core import structs, config, utils, blockchain
from ..exceptions.tx_exceptions import InsufficientFundsError


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame, padding=10)

        self.refresh_data_rate = 1000  # milliseconds

        self.display_units = config.UNITS
        self.unit_factor = config.UNIT_FACTORS[self.display_units]
        self.max_decimal_places = config.UNITS_MAX_DECIMAL_PLACES[self.display_units]

        # attributes below will be updated in _refresh_data method
        self.wallet_balance = tk.IntVar()
        self.unconfirmed_wallet_balance = tk.IntVar()
        self.price = tk.IntVar()
        self.fiat_wallet_balance = tk.IntVar()
        self.unconfirmed_fiat_wallet_balance = tk.IntVar()

        self.next_receiving_address = tk.StringVar()

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

        receive_display = _ReceiveDisplay(notebook, self)
        receive_display.grid(sticky='nsew')
        notebook.add(receive_display, text='Receive')

        notebook.grid(row=1, column=0, pady=(0, 10))

        self._draw_bottom_info_bar()
        self._draw_menu_bar()
        self._refresh_data()

    def _draw_menu_bar(self):
        menu_bar = tk.Menu(self.root)

        wallet_menu = tk.Menu(menu_bar, tearoff=0)
        wallet_menu.add_command(label='Information')
        wallet_menu.add_separator()
        wallet_menu.add_command(label='Show Mnemonic')
        wallet_menu.add_command(label='Change Password')

        options_menu = tk.Menu(menu_bar, tearoff=0)
        options_menu.add_command(label='Settings', command=self.root.settings_prompt)


        menu_bar.add_cascade(label='Wallet', menu=wallet_menu)
        menu_bar.add_cascade(label='Options', menu=options_menu)

        self.root.config(menu=menu_bar)

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

        self.next_receiving_address.set(self.root.btc_wallet.receiving_addresses[0])

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

        self.tree_view.column('#0', minwidth=100, width=100)
        self.tree_view.column('#1', minwidth=400, width=400)
        self.tree_view.column('#2', minwidth=120, width=120)
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
        # initialise txn with no outputs to prevent race condition when accessing txn size
        # (size wont be accurate though, obviously)
        self.transaction = self.btc_wallet.make_unsigned_transaction({})
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

        self.amount_fiat_var = tk.StringVar(value='0.0')
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

        self.total_cost_var = tk.StringVar(value='0.0')
        self.total_cost = ttk.Label(total_cost_frame, textvariable=self.total_cost_var,
                                    font=self.main_wallet.root.small_font, width=15)
        self.total_cost.grid(row=0, column=0, pady=5, padx=21, sticky='w')

        total_fiat_cost_label = ttk.Label(total_cost_frame, text=f'Total ({config.FIAT}):',
                                          font=self.main_wallet.root.small_font)
        total_fiat_cost_label.grid(row=0, column=2, sticky='w')

        self.total_fiat_cost_var = tk.StringVar(value='0.0')
        self.total_fiat_cost = ttk.Label(total_cost_frame, textvariable=self.total_fiat_cost_var,
                                    font=self.main_wallet.root.small_font, width=15)
        self.total_fiat_cost.grid(row=0, column=3, padx=36, sticky='w')

        total_cost_frame.grid(row=3, column=1, pady=5, sticky='w')

        send_button = ttk.Button(self, text='Send', command=self.on_send)
        send_button.grid(row=4, column=0, pady=20, padx=10, sticky='e')

        clear_button = ttk.Button(self, text='Clear', command=self.on_clear)
        clear_button.grid(row=4, column=1, pady=20, padx=10, sticky='w')

    def on_send(self):
        if not all((self.amount_btc_entry.get(), self.fee_entry.get(), self.address_entry.get())):
            tk.messagebox.showerror('Invalid Entries', 'Please fill out all entries before sending')

        elif self.amount_over_balance:
            tk.messagebox.showerror('Insufficient Funds', 'Amount to send exceeds wallet balance')

        elif float(self.amount_btc_entry.get()) <= 0 or \
                float(self.amount_btc_entry.get()) <= 0 or \
                int(self.fee_entry.get()) <= 0:
            tk.messagebox.showerror('Invalid Amount(s)', 'Amount(s) must be positive, non-zero, numbers')

        else:
            self.sign_transaction_window()

    def on_clear(self):
        self._make_transaction_thread_event.set()
        self._thread_running = False

        self.amount_btc_entry.delete(0, tk.END)
        self.fee_entry.delete(0, tk.END)
        self.fee_entry['state'] = tk.DISABLED
        self.amount_btc_entry['state'] = tk.DISABLED

        self.address_entry['state'] = tk.NORMAL
        self.address_entry.delete(0, tk.END)

        self.total_fiat_cost_var.set('0.0')

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
        fiat_amount = round(float(self.main_wallet.price.get()) * self.to_btc(amount), 2)
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
            self.amount_fiat_var.set('0.0')
            self.total_cost_var.set('0.0')

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
            self.amount_fiat_var.set('0.0')
            return 

        value = float(event.widget.get())
        fiat_amount = self.to_fiat(value)

        self.amount_fiat_var.set(utils.float_to_str(fiat_amount))

    def _totals_set(self):
        amount, fee = 0.0, 0

        if self.amount_btc_entry.get():
            amount = float(self.amount_btc_entry.get())

        if self.fee_entry.get():
            sat_byte = int(self.fee_entry.get())

            # fee is in satoshis so needs to be divided by unit factor
            fee = (sat_byte * self.transaction.estimated_size()) / self.main_wallet.unit_factor

        if self.to_satoshis(amount) < 1 or self.amount_over_balance:
            self.hide_fee_labels()

        elif self.fee_labels_hidden:
            self.show_fee_labels()

        size = self.transaction.estimated_size()
        total_fee =  utils.float_to_str(round(fee, self.main_wallet.max_decimal_places))
        total_cost = utils.float_to_str(round(amount + fee, self.main_wallet.max_decimal_places))
        total_fiat_cost = utils.float_to_str(self.to_fiat(float(total_cost)))

        self.size_label_var.set(size)
        self.total_fee_var.set(total_fee)
        self.total_cost_var.set(total_cost)
        self.total_fiat_cost_var.set(total_fiat_cost)

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
            self.total_fiat_cost.config(foreground=colour)

            # changing colours when they are hidden will cause them to re-appear
            if not self.fee_labels_hidden:
                self.total_fee.config(foreground=colour)

        while not self._make_transaction_thread_event.is_set():
            time.sleep(0.05)

            amount, fee_entry = 0, 0

            address = self.address_entry.get()

            if self.amount_btc_entry.get():
                amount = self.to_satoshis(float(self.amount_btc_entry.get()))

            if self.fee_entry.get():
                fee_entry = int(self.fee_entry.get())

            # only recreate transaction if values are different
            if (amount, fee_entry) in cached_txns:
                set_amounts_colour('black')
                # txns that are cached are not spending above wallet balance,
                # they are only cached after a successful init
                self.amount_over_balance = False

                self.transaction = cached_txns[(amount, fee_entry)]

            else:

                try:
                    transaction = self.btc_wallet.make_unsigned_transaction(
                        outs_amounts={address: amount}
                    )

                    transaction.change_fee_sat_byte(fee_entry)

                    cached_txns[(amount, fee_entry)] = transaction
                    self.transaction = transaction

                    # update transaction size/total fee if changing fee changed
                    # the size. May not be needed if this thread can update
                    # self.transaction before the bound entry methods can call
                    # self._totals_set. but that obviously can't be counted on,
                    # so we call it here as well
                    self._totals_set()

                    set_amounts_colour('black')
                    self.amount_over_balance = False

                except InsufficientFundsError:
                    set_amounts_colour('red')
                    self.amount_over_balance = True

        else:
            set_amounts_colour('black')

    def on_btc_amount_key_press(self, event):
        self._amount_btc_entry_to_fiat(event)
        self._totals_set()

    def on_fee_key_press(self):
        self._totals_set()

    def sign_transaction_window(self):

        window = tk.Toplevel(self)
        window.iconbitmap(self.main_wallet.root.ICON)

        bold_title = self.main_wallet.root.bold_title_font
        bold_small = self.main_wallet.root.small_font + ('bold',)
        small = self.main_wallet.root.small_font

        # block interaction with root window
        window.grab_set()

        @utils.threaded
        def sign_and_broadcast(load_window, password):

            def on_copy_txid():
                self.main_wallet.root.clipboard_clear()
                self.main_wallet.root.clipboard_append(self.transaction.txn.txid)

            self.btc_wallet.sign_transaction(self.transaction, password)
            response_status = blockchain.broadcast_transaction(self.transaction.txn.hexlify())

            # stop txn making thread and clear inputs, after transaction has
            # been broadcast and is final
            self.on_clear()

            # if the broadcast failed
            if not response_status:
                load_window.destroy()
                tk.messagebox.showerror('Broadcast Error', 'Unable to broadcast transaction! '
                                                           '(Please check your internet connection)')
                return

            load_window.destroy()
            sent_window = tk.Toplevel(self)
            sent_window.iconbitmap(self.main_wallet.root.ICON)
            title_ = ttk.Label(sent_window, text='Transaction Sent!', font=bold_title)
            title_.grid(padx=20, pady=20)

            txid = ttk.Label(sent_window, text=f'TXID: {self.transaction.txn.txid}',
                             font=bold_small)
            txid.grid(padx=20, pady=20)

            button_frame_ = ttk.Frame(sent_window)

            ok_button = ttk.Button(button_frame_, text='OK', command=lambda: sent_window.destroy())
            ok_button.grid(row=0, column=0, padx=10, pady=10)

            copy_button = ttk.Button(button_frame_, text='Copy TXID', command=on_copy_txid)
            copy_button.grid(row=0, column=1, padx=10, pady=10)

            button_frame_.grid()

        def on_send():
            password = self.main_wallet.root.password_prompt(window)

            # if cancel was pressed
            if password is None:
                return

            if not self.btc_wallet.data_store.validate_password(password):
                self.main_wallet.root.incorrect_password_prompt(window)
                return

            window.destroy()
            info = tk.Toplevel(self)
            info.iconbitmap(self.main_wallet.root.ICON)

            title_ = ttk.Label(info, text='Signing & Broadcasting transaction, please wait...',
                               font=bold_title)
            title_.grid(pady=20, padx=20)

            load_bar = ttk.Progressbar(info, mode='indeterminate')
            load_bar.grid(pady=20, padx=20)
            load_bar.start()

            sign_and_broadcast(info, password)

        def on_cancel():
            window.destroy()

        title = ttk.Label(window, text='TRANSACTION CONFIRMATION',
                          font=self.main_wallet.root.bold_title_font)
        title.grid(row=0, column=0, pady=20, sticky='n')

        info_frame = ttk.Frame(window)

        address_receiving_label = ttk.Label(info_frame, text='RECEIVING ADDRESS:',
                                            font=bold_small)
        address_receiving_label.grid(row=0, column=0, padx=20, sticky='w')

        address = ttk.Label(info_frame, text=list(self.transaction.outputs_amounts.keys())[0],
                            font=small)
        address.grid(row=0, column=1, padx=20)

        amount_label = ttk.Label(info_frame, text='AMOUNT TO SEND:',
                                 font=bold_small)
        amount_label.grid(row=1, column=0, padx=20, pady=5, sticky='w')

        amount = ttk.Label(info_frame, text=f'{self.amount_btc_entry.get()} '
                                            f'{self.main_wallet.display_units}',
                           font=small)
        amount.grid(row=1, column=1, padx=20)

        fee_label = ttk.Label(info_frame, text='FEE:', font=bold_small)
        fee_label.grid(row=2, column=0, padx=20, pady=5, sticky='w')

        fee = ttk.Label(info_frame, text=f'{self.fee_entry.get()} sat/byte '
                                         f'(total: {self.total_fee_var.get()} '
                                         f'{self.main_wallet.display_units})',
                        font=small)
        fee.grid(row=2, column=1, padx=20)

        total_cost_label = ttk.Label(info_frame, text='TOTAL COST:', font=bold_small)
        total_cost_label.grid(row=3, column=0, padx=20, pady=5, sticky='w')

        total_cost = ttk.Label(info_frame, text=f'{self.total_cost_var.get()} '
                                                f'{self.main_wallet.display_units}',
                               font=small)
        total_cost.grid(row=3, column=1, padx=20)

        # if there will be a dust change amount discarded, show a message
        if self.transaction.dust_change_amount > 0:
            dust_notify_label = ttk.Label(info_frame, text='NOTE:', font=bold_small)
            dust_notify_label.grid(row=4, column=0, padx=20, pady=5, sticky='w')

            dust_msg = ttk.Label(info_frame, text=f'{utils.float_to_str(self.transaction.dust_change_amount / self.main_wallet.unit_factor)} '
                                                  f'{self.main_wallet.display_units} will be added to the fee, as it is considered a '
                                                  f'"dust" amount, and would be un-spendable if sent to a change address',
                                 font=small, wraplength=400, justify=tk.CENTER)
            dust_msg.grid(row=4, column=1, padx=20)

        info_frame.grid(row=1)

        button_frame = ttk.Frame(window)

        send_button = ttk.Button(button_frame, text='Send', command=on_send)
        send_button.grid(row=0, column=0, padx=10, pady=10)

        cancel_button = ttk.Button(button_frame, text='Cancel', command=on_cancel)
        cancel_button.grid(row=0, column=1, padx=10, pady=10)

        button_frame.grid(row=2, column=0, padx=10, pady=10)


class _ReceiveDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master, padding=5)
        self.main_wallet = main_wallet

        self.grid_rowconfigure(0, {'minsize': 10})

        self.address_label = ttk.Label(self, text='Receiving Address:',
                                       font=self.main_wallet.root.small_font + ('bold',))
        self.address_label.grid(row=1, column=0, sticky='w', padx=10)

        self.address = tk.Text(self, height=1, width=40, font=self.main_wallet.root.small_font)
        self.address['state'] = tk.DISABLED
        self.address.configure(inactiveselectbackground=self.address.cget("selectbackground"))
        self.address.grid(row=1, column=1, padx=20)

        self.qr = None
        self.qr_label = None
        self.draw_qr_code()

        self._update_address()

    def _update_address(self):
        """ a text widget is used for address display as it is copyable, however
         it doesn't have a textvariable param so the address is updated here
        """
        # if the address has changed, then update text
        if self.address.get(1.0, 'end-1c') != self.main_wallet.next_receiving_address.get():
            self.address['state'] = tk.NORMAL

            self.address.delete(1.0, tk.END)
            self.address.insert(tk.END, self.main_wallet.next_receiving_address.get())

            self.address['state'] = tk.DISABLED

            # update qr code with new address
            self.draw_qr_code()

        self.main_wallet.root.after(self.main_wallet.refresh_data_rate, self._update_address)

    def _make_qr_code(self):
        qr = qrcode.QRCode(box_size=5)
        qr.add_data(self.main_wallet.next_receiving_address.get())

        tk_image = ImageTk.PhotoImage(qr.make_image(back_color='#F0F0F0'))
        return tk_image

    def draw_qr_code(self):
        # keep reference to image or it will be garbage collected
        self.qr = self._make_qr_code()
        self.qr_label = ttk.Label(self, image=self.qr)
        self.qr_label.grid(row=1, column=2)
