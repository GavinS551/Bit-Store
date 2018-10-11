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
from tkinter import ttk, messagebox, filedialog

import string
import pathlib
from threading import Event
from types import SimpleNamespace

from ...core import config, utils
from ...core.tx import InsufficientFundsError


class SendDisplay(ttk.Frame):
    """ beware of spaghetti code """

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master, padding=5)
        self.main_wallet = main_wallet

        # NB: Most tk Variables are defined as string vars, so floats can be
        # represented without scientific notation, using the utils function
        # "float_to_str"

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

        amount_fiat_label = ttk.Label(amount_frame, text=f'Amount ({config.get_value("FIAT")}):',
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
        self.fee_entry['state'] = tk.DISABLED  # enabled after address entry
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

        total_fiat_cost_label = ttk.Label(total_cost_frame, text=f'Total ({config.get_value("FIAT")}):',
                                          font=self.main_wallet.root.small_font)
        total_fiat_cost_label.grid(row=0, column=2, sticky='w')

        self.total_fiat_cost_var = tk.StringVar(value='0.0')
        self.total_fiat_cost = ttk.Label(total_cost_frame, textvariable=self.total_fiat_cost_var,
                                         font=self.main_wallet.root.small_font, width=15)
        self.total_fiat_cost.grid(row=0, column=3, padx=36, sticky='w')

        total_cost_frame.grid(row=3, column=1, pady=5, sticky='w')

        button_frame = ttk.Frame(self)

        # send button is cls attribute as it will have to be accessed by subclasses such
        # as a public btc wallet implementation that cannot sign txns
        self.send_button = ttk.Button(button_frame, text='Send', command=self.on_send)
        self.send_button.grid(row=0, column=0, pady=20, padx=10)

        export_button = ttk.Button(button_frame, text='Export Txn', command=self.export_txn)
        export_button.grid(row=0, column=1, pady=20, padx=10)

        import_button = ttk.Button(button_frame, text='Import Txn', command=self.on_import)
        import_button.grid(row=0, column=2, pady=20, padx=10)

        use_balance_button = ttk.Button(button_frame, text='Use Balance', command=self.on_use_balance)
        use_balance_button.grid(row=0, column=3, pady=20, padx=10)

        clear_button = ttk.Button(button_frame, text='Clear', command=self.on_clear)
        clear_button.grid(row=0, column=4, pady=20, padx=10)

        button_frame.grid(row=4, column=0, columnspan=3, sticky='w', padx=(20, 0))

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
            self.send_transaction_window()

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

    def on_use_balance(self):

        if not utils.validate_address(self.address_entry.get()):
            tk.messagebox.showerror('No Address', 'Please enter an address first')

        elif not self.fee_entry.get():
            tk.messagebox.showerror('No fee', 'Please enter what fee you want to use')

        else:
            balance = self.main_wallet.wallet_balance.get() if not config.get_value('SPEND_UNCONFIRMED_UTXOS') else \
                self.main_wallet.wallet_balance.get() + \
                self.main_wallet.unconfirmed_wallet_balance.get()
            sat_balance = self.to_satoshis(balance)

            fee_entry = int(self.fee_entry.get())  # sat/byte

            # generating txn that spends all btc, and getting size
            _txn = self.main_wallet.root.btc_wallet.make_unsigned_transaction({self.address_entry.get(): sat_balance})

            max_spend_size = _txn.estimated_size()

            sat_total_fee = fee_entry * max_spend_size

            sat_remaining_balance = sat_balance - sat_total_fee

            wallet_units_remaining_balance = self.to_wallet_units(sat_remaining_balance, 'sat')

            # 1 sat/byte is lowest fee that can be used, i.e 1 * max_spend_size
            if sat_balance <= max_spend_size:
                wallet_units_remaining_balance = 0

            self.amount_btc_entry.delete(0, tk.END)
            self.amount_btc_entry.insert(tk.END, utils.float_to_str(wallet_units_remaining_balance))

            # call the method that is bound to key releases on btc_entry
            self.on_btc_amount_key_press(event=SimpleNamespace(widget=self.amount_btc_entry))

    def on_import(self):
        file_path = filedialog.askopenfilename(title='Import Transaction',
                                               initialdir=pathlib.Path.home(),
                                               filetypes=[('Transaction Files', '*.txn')])

        if not file_path:
            return

        try:
            txn = self.btc_wallet.file_import_transaction(file_path)

            if not txn.is_signed and self.main_wallet.root.is_watch_only:
                messagebox.showerror('Error', 'Cannot import unsigned transaction in watch-only wallet')
                return

        except ValueError as ex:
            messagebox.showerror('Error', str(ex))
            return

        self.on_clear()
        self.transaction = txn

        # ignore asserts that check what gui is displaying, and what self.transaction actually is,
        # as the gui entries won't be filled correctly
        self.send_transaction_window(ignore_asserts=True)

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

    def to_wallet_units(self, amount, units):
        if units not in config.POSSIBLE_BTC_UNITS:
            raise ValueError(f'Invalid btc unit: {units}')

        return round((config.UNIT_FACTORS[units] * amount) / self.main_wallet.unit_factor,
                     self.main_wallet.max_decimal_places)

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

    def _entry_btc_amount_validate(self, entered, entry, before_change, force_satoshis=False):
        """ validates that anything entered in amount entries are valid numbers """

        units = self.main_wallet.display_units if not force_satoshis else 'sat'
        max_decimal = self.main_wallet.max_decimal_places if not force_satoshis else 0

        for char in entered:
            if char in string.digits + '.' and not entry.count('.') > 1 and not entry == '.':

                if entry.count('.') == 1 and units != 'sat':
                    if len(entry.split('.')[1]) <= max_decimal:
                        continue
                    else:
                        return False

                # satoshi units are not divisible
                elif entry.count('.') == 1 and units == 'sat':
                    return False

                else:
                    continue

            # for deleting the whole, or part of, the entry
            elif not entry or entry in before_change:
                continue

            else:
                return False

        else:
            return True

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
            # fee is in satoshis so needs to be divided by unit factor
            fee = self.transaction.fee / self.main_wallet.unit_factor

        if self.to_satoshis(amount) < 1 or self.amount_over_balance:
            self.hide_fee_labels()

        else:
            self.show_fee_labels()

        size = self.transaction.estimated_size()
        total_fee = utils.float_to_str(round(fee, self.main_wallet.max_decimal_places))
        total_cost = utils.float_to_str(round(amount + fee, self.main_wallet.max_decimal_places))
        total_fiat_cost = utils.float_to_str(self.to_fiat(float(total_cost)))

        self.size_label_var.set(size)
        self.total_fee_var.set(total_fee)
        self.total_cost_var.set(total_cost)
        self.total_fiat_cost_var.set(total_fiat_cost)

    @utils.threaded(daemon=True, name='GUI_MAKE_TXN_THREAD')
    def _make_transaction(self):

        # to ensure only one thread is run at the same time
        if self._thread_running:
            return
        else:
            self._thread_running = True  # if it wasn't already set

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
            # to prevent the gui window from lagging
            self._make_transaction_thread_event.wait(0.05)

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

                    # change address will be set when fee is changed
                    # there is a reason for this but I forgot, so don't change it
                    transaction = self.btc_wallet.make_unsigned_transaction(
                        outs_amounts={address: amount}
                    )

                    transaction.change_fee_sat_byte(fee_entry)

                    cached_txns[(amount, fee_entry)] = transaction

                    # to make sure that when the event is set, you can be sure that self.transaction
                    # will not be overridden
                    if not self._make_transaction_thread_event.is_set():
                        self.transaction = transaction
                    else:
                        break

                    set_amounts_colour('black')
                    self.amount_over_balance = False

                    # update transaction size/total fee if changing fee changed
                    # the size. May not be needed if this thread can update
                    # self.transaction before the bound entry methods can call
                    # self._totals_set. but that obviously can't be counted on,
                    # so we call it here as well
                    self._totals_set()

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

    def send_transaction_window(self, ignore_asserts=False):

        is_signed = self.transaction.is_signed

        if not ignore_asserts:
            # make sure that what the gui is adding up, and what the transaction
            # instance actually totals to, are equal.
            tx_total = sum(self.transaction.outputs_amounts.values()) + self.transaction.fee
            assert self.to_satoshis(float(self.total_cost_var.get())) == tx_total
            assert self.to_satoshis(float(self.total_fee_var.get())) == self.transaction.fee

        # warn user about a dust output
        if self.transaction.output_contains_dust:
            tk.messagebox.showwarning('Dust Output',
                                      'Warning: Transaction output contains a dust amount. '
                                      'This is not recommended as the fee you pay may '
                                      'cost more than what you are sending, and the transaction '
                                      'may take longer to confirm.')

        window = self.main_wallet.root.get_toplevel(self, resizable=True)

        bold_title = self.main_wallet.root.bold_title_font
        bold_small = self.main_wallet.root.small_font + ('bold',)
        small = self.main_wallet.root.small_font

        # block interaction with root window
        window.grab_set()

        @utils.threaded(daemon=True, name='GUI_SIGN_AND_BROADCAST_THREAD')
        def sign_and_broadcast(load_window, password):

            if not is_signed:
                self.btc_wallet.sign_transaction(self.transaction, password)

            response_status, response_code = self.btc_wallet.broadcast_transaction(self.transaction)

            signed_txid = self.transaction.txid

            # if the broadcast failed
            if not response_status:
                load_window.destroy()
                if response_code is None:
                    status_str = f'(Connection Error)'
                else:
                    status_str = f'(Status code: {response_code})'

                tk.messagebox.showerror('Broadcast Error', 'Unable to broadcast transaction! '
                                                           f'{status_str}')
                return

            # stop txn making thread and clear inputs, after transaction has
            # been broadcast and is final
            self.on_clear()

            def on_copy_txid():
                self.main_wallet.root.clipboard_clear()
                self.main_wallet.root.clipboard_append(signed_txid)
                self.main_wallet.root.update()

            load_window.destroy()
            sent_window = self.main_wallet.root.get_toplevel(self, resizable=True)

            title_ = ttk.Label(sent_window, text='Transaction Sent!', font=bold_title)
            title_.grid(padx=20, pady=20)

            txid = ttk.Label(sent_window, text=f'TXID: {signed_txid}',
                             font=bold_small)
            txid.grid(padx=20, pady=20)

            button_frame_ = ttk.Frame(sent_window)

            ok_button = ttk.Button(button_frame_, text='OK', command=sent_window.destroy)
            ok_button.grid(row=0, column=0, padx=10, pady=10)

            copy_button = ttk.Button(button_frame_, text='Copy TXID', command=on_copy_txid)
            copy_button.grid(row=0, column=1, padx=10, pady=10)

            button_frame_.grid()

        def on_send():
            if not is_signed:
                password = self.main_wallet.root.password_prompt(window)

                # if cancel was pressed
                if password is None:
                    return

                if not self.btc_wallet.data_store.validate_password(password):
                    self.main_wallet.root.incorrect_password_prompt(window)
                    return

            else:
                password = None

            window.destroy()
            info = tk.Toplevel(self)
            info.iconbitmap(self.main_wallet.root.ICON)

            title_str = 'Signing & Broadcasting transaction, please wait...' if not is_signed \
                else 'Broadcasting transaction, please wait...'
            title_ = ttk.Label(info, text=title_str,
                               font=bold_title)
            title_.grid(pady=20, padx=20)

            load_bar = ttk.Progressbar(info, mode='indeterminate')
            load_bar.grid(pady=20, padx=20)
            load_bar.start()

            sign_and_broadcast(info, password)

        def on_sign_export():
            password = self.main_wallet.root.password_prompt(window)
            if not password:
                return

            self.btc_wallet.sign_transaction(self.transaction, password)
            # ignore entry check as an imported unsigned txn can be imported without entries filled
            self.export_txn(ignore_entry_check=True)
            window.destroy()

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

        amt = utils.float_to_str(self.to_wallet_units(list(self.transaction.outputs_amounts.values())[0],
                                                      'sat'))
        amount = ttk.Label(info_frame, text=f'{amt} '
                                            f'{self.main_wallet.display_units}',
                           font=small)
        amount.grid(row=1, column=1, padx=20)

        fee_label = ttk.Label(info_frame, text='FEE:', font=bold_small)
        fee_label.grid(row=2, column=0, padx=20, pady=5, sticky='w')

        total_fee = utils.float_to_str(self.to_wallet_units(self.transaction.fee, "sat"))
        fee = ttk.Label(info_frame, text=f'{self.transaction.fee_sat_byte} sat/byte '
                                         f'(total: {total_fee} '
                                         f'{self.main_wallet.display_units})',
                        font=small)
        fee.grid(row=2, column=1, padx=20)

        total_cost_label = ttk.Label(info_frame, text='TOTAL COST:', font=bold_small)
        total_cost_label.grid(row=3, column=0, padx=20, pady=5, sticky='w')

        sat_total = self.transaction.fee + list(self.transaction.outputs_amounts.values())[0]
        total = utils.float_to_str(self.to_wallet_units(sat_total, 'sat'))
        total_cost = ttk.Label(info_frame, text=f'{total} '
                                                f'{self.main_wallet.display_units}',
                               font=small)
        total_cost.grid(row=3, column=1, padx=20)

        is_signed_label = ttk.Label(info_frame, text='IS SIGNED:', font=bold_small)
        is_signed_label.grid(row=4, column=0, padx=20, pady=5, sticky='w')

        is_signed_ = ttk.Label(info_frame, text=str(is_signed), font=small)
        is_signed_.grid(row=4, column=1, padx=20)

        # if there will be a dust change amount discarded, show a message
        if self.transaction.dust_change_amount > 0:
            dust_notify_label = ttk.Label(info_frame, text='NOTE:', font=bold_small)
            dust_notify_label.grid(row=5, column=0, padx=20, pady=5, sticky='w')

            dust_amt = utils.float_to_str(self.transaction.dust_change_amount / self.main_wallet.unit_factor)
            dust_msg = ttk.Label(info_frame,
                                 text=f'{dust_amt} {self.main_wallet.display_units} will be added to the fee, '
                                      f'because if it was sent to a change address it would be un-spendable\n'
                                      f'(the transaction fee needed to spend it would cost more than what the amount '
                                      f'is worth)',
                                 font=small, wraplength=400, justify=tk.CENTER)
            dust_msg.grid(row=5, column=1, padx=20)

        info_frame.grid(row=1)

        button_frame = ttk.Frame(window)

        send_button = ttk.Button(button_frame, text='Send', command=on_send)
        send_button.grid(row=0, column=0, padx=10, pady=10)

        if not is_signed:
            sign_export_button = ttk.Button(button_frame, text='Sign & Export',
                                            command=on_sign_export)
            sign_export_button.grid(row=0, column=1, padx=10, pady=10)

        cancel_button = ttk.Button(button_frame, text='Cancel', command=on_cancel)
        cancel_button.grid(row=0, column=2, padx=10, pady=10)

        button_frame.grid(row=2, column=0, padx=10, pady=10)

    def export_txn(self, ignore_entry_check=False):
        if not ignore_entry_check:
            if not all((self.amount_btc_entry.get(), self.fee_entry.get(), self.address_entry.get())):
                tk.messagebox.showerror('Invalid Entries', 'Please fill out all entries before sending')
                return

            elif self.amount_over_balance:
                tk.messagebox.showerror('Insufficient Funds', 'Amount to send exceeds wallet balance')
                return

            elif float(self.amount_btc_entry.get()) <= 0 or \
                    float(self.amount_btc_entry.get()) <= 0 or \
                    int(self.fee_entry.get()) <= 0:
                tk.messagebox.showerror('Invalid Amount(s)', 'Amount(s) must be positive, non-zero, numbers')
                return

        default_name = 'signed.txn' if self.transaction.is_signed else 'unsigned.txn'

        export_path = filedialog.asksaveasfilename(title='Export Transaction',
                                                   initialdir=pathlib.Path.home(),
                                                   initialfile=default_name,
                                                   filetypes=[('Transaction Files', '*.txn')])

        if not export_path:
            return

        # append file extension if its not there
        if not export_path.split('.')[-1] == 'txn':
            export_path += '.txn'

        try:
            self.main_wallet.root.btc_wallet.file_export_transaction(file_path=export_path,
                                                                     transaction=self.transaction)
        except OSError as ex:
            messagebox.showerror('Error', f'Unable to export transaction: {ex.__str__()}')

        else:
            self.on_clear()
            messagebox.showinfo('Transaction Exported', 'Transaction was successfully exported')
