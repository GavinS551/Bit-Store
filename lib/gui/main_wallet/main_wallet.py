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
from tkinter import ttk, messagebox

import sys

from ._tx_display import TransactionDisplay
from ._send_display import SendDisplay
from ._receive_display import ReceiveDisplay
from ._console_display import ConsoleDisplay
from ._address_display import AddressDisplay

from ...core import config, utils, data, blockexplorer


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame, padding=5)

        self.refresh_data_rate = 1000  # milliseconds

        self.display_units = config.get('BTC_UNITS')
        self.unit_factor = config.UNIT_FACTORS[self.display_units]
        self.max_decimal_places = config.UNITS_MAX_DECIMAL_PLACES[self.display_units]

        # defined in gui_draw
        self.notebook = None
        self.tx_display = None
        self.send_display = None
        self.receive_display = None
        self.address_display = None
        self.console_display = None
        self.title_label = None

        self.menu_bar = None
        self.wallet_menu = None
        self.options_menu = None

        # attributes below will be updated in _refresh_data method
        self.wallet_balance = tk.DoubleVar()
        self.unconfirmed_wallet_balance = tk.DoubleVar()
        self.price = tk.DoubleVar()
        self.fiat_wallet_balance = tk.StringVar()
        self.unconfirmed_fiat_wallet_balance = tk.StringVar()
        self.estimated_fees = (tk.IntVar(), tk.IntVar(), tk.IntVar())  # low, medium, high priority

        self.next_receiving_address = tk.StringVar()

        self.api_thread_status = tk.StringVar()

        self.block_explorer = blockexplorer.explorer_api(config.get('BLOCK_EXPLORER_SOURCE'))

    def gui_draw(self):
        self._refresh_data()

        self.title_label = ttk.Label(self, text=self.root.btc_wallet.name,
                                     font=self.root.bold_title_font)
        self.title_label.grid(row=0, column=0, pady=(0, 10))

        self.notebook = ttk.Notebook(self)
        self.notebook.enable_traversal()

        self.tx_display = TransactionDisplay(self.notebook, self)
        self.tx_display.grid(sticky='nsew')
        self.notebook.add(self.tx_display, text='Transactions', underline=0)

        self.send_display = SendDisplay(self.notebook, self)
        self.send_display.grid(sticky='nsew')
        self.notebook.add(self.send_display, text='Send', underline=0)

        self.receive_display = ReceiveDisplay(self.notebook, self)
        self.receive_display.grid(sticky='nsew')
        self.notebook.add(self.receive_display, text='Receive', underline=0)

        self.address_display = AddressDisplay(self.notebook, self)
        self.address_display.grid(sticky='nsew')
        self.notebook.add(self.address_display, text='Addresses', underline=0)

        self.console_display = ConsoleDisplay(self.notebook, self)
        self.console_display.grid(sticky='nsew')
        self.notebook.add(self.console_display, text='Console', underline=0)

        self.notebook.grid(row=1, column=0, pady=(0, 10))

        self._draw_bottom_info_bar()
        self._draw_menu_bar()
        self._draw_api_status()

    def to_satoshis(self, amount):
        """ converts amount (in terms of self.display_units) into satoshis"""
        return int(round(amount * self.unit_factor))

    def to_btc(self, amount):
        """ converts different units into btc, (needed as price is in terms of btc) """
        if self.display_units == 'BTC':
            return amount
        else:
            btc = self.to_satoshis(amount) / config.UNIT_FACTORS['BTC']
            return btc

    def to_wallet_units(self, amount, units):
        if units not in config.POSSIBLE_BTC_UNITS:
            raise ValueError(f'Invalid btc unit: {units}')

        return round((config.UNIT_FACTORS[units] * amount) / self.unit_factor,
                     self.max_decimal_places)

    def to_fiat(self, amount):
        """ converts amount (display units) into fiat value """
        fiat_amount = round(float(self.price.get()) * self.to_btc(amount), 2)
        return fiat_amount

    def display_txn(self, txn):
        """ txn must be a structs.TransactionData object. Info will be displayed about it
        in top level window
        """
        TransactionView(self, txn)

    def _draw_menu_bar(self):
        self.menu_bar = tk.Menu(self.root)

        self.wallet_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.wallet_menu.add_command(label='Information', command=self._info_window)
        self.wallet_menu.add_separator()
        self.wallet_menu.add_command(label='Display Mnemonic', command=self._mnemonic_window)
        self.wallet_menu.add_command(label='Change Password', command=self._change_password_window)

        self.options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.options_menu.add_command(label='Settings', command=self.root.settings_prompt)
        self.options_menu.add_separator()
        self.options_menu.add_command(label='Hide Addresses')
        self.options_menu.add_command(label='Hide Console')

        self.menu_bar.add_cascade(label='Wallet', menu=self.wallet_menu)
        self.menu_bar.add_cascade(label='Options', menu=self.options_menu)
        self.menu_bar.add_command(label='About', command=self._about_window)

        self.root.config(menu=self.menu_bar)

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
        fiat_balance_label = ttk.Label(fiat_balance_frame, text=f'{config.get("FIAT")} Balance:',
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

    def _draw_api_status(self):
        status_frame = ttk.Frame(self)

        status_label = ttk.Label(status_frame, textvariable=self.api_thread_status, font=self.root.tiny_font)
        status_label.grid(row=0, column=0)

        status_frame.grid(pady=(10, 0))

    def _change_password_window(self):
        data_store = self.root.btc_wallet.data_store

        change_pass_window = self.root.get_toplevel(self)
        change_pass_window.grab_set()

        def on_ok():
            incorrect = False
            if not data_store.validate_password(old_password_entry.get()):
                tk.messagebox.showerror('Incorrect Password', 'Old Password is incorrect, try again.',
                                        parent=change_pass_window)
                incorrect = True

            elif not new_password_entry.get() == new_password_confirm_entry.get():
                tk.messagebox.showerror('Password Validation', 'New password entries do not match, try again.',
                                        parent=change_pass_window)
                incorrect = True

            elif '' in (new_password_entry.get(), new_password_confirm_entry.get()):
                tk.messagebox.showerror('Blank Password', 'Password cannot be blank',
                                        parent=change_pass_window)
                incorrect = True

            if incorrect:
                old_password_entry.delete(0, tk.END)
                new_password_entry.delete(0, tk.END)
                new_password_confirm_entry.delete(0, tk.END)
                return

            data_store.change_password(new_password_entry.get())
            change_pass_window.destroy()
            tk.messagebox.showinfo('Password Changed', 'Password change successful.')

        def on_cancel():
            change_pass_window.destroy()

        change_pass_frame = ttk.Frame(change_pass_window, padding=10)

        title_label = ttk.Label(change_pass_frame, text='Change Password:', font=self.root.small_font + ('bold',))
        title_label.grid(row=0, column=0, pady=(0, 10), padx=10, sticky='w')

        old_password_label = ttk.Label(change_pass_frame, text='Old Password:',
                                       font=self.root.small_font)
        old_password_label.grid(row=1, column=0, pady=5, padx=10, sticky='w')

        old_password_entry = ttk.Entry(change_pass_frame, show='●')
        old_password_entry.grid(row=1, column=1)

        new_password_label = ttk.Label(change_pass_frame, text='New Password:',
                                       font=self.root.small_font)
        new_password_label.grid(row=2, column=0, pady=5, padx=10, sticky='w')

        new_password_entry = ttk.Entry(change_pass_frame, show='●')
        new_password_entry.grid(row=2, column=1)

        new_password_confirm_label = ttk.Label(change_pass_frame, text='Confirm Password:',
                                               font=self.root.small_font)
        new_password_confirm_label.grid(row=3, column=0, pady=5, padx=10, sticky='w')

        new_password_confirm_entry = ttk.Entry(change_pass_frame, show='●')
        new_password_confirm_entry.grid(row=3, column=1)

        button_frame = ttk.Frame(change_pass_frame)

        enter_button = ttk.Button(button_frame, text='OK', command=on_ok)
        enter_button.grid(row=0, column=0, padx=10, pady=(10, 0), sticky='e')

        cancel_button = ttk.Button(button_frame, text='Cancel', command=on_cancel)
        cancel_button.grid(row=0, column=1, padx=10, pady=(10, 0), sticky='w')

        button_frame.grid(row=4, column=0, columnspan=2)

        change_pass_frame.grid(row=0, column=0, sticky='nsew')

    def _refresh_data(self):
        f2s = utils.float_to_str
        self.wallet_balance.set(self.root.btc_wallet.wallet_balance / self.unit_factor)
        self.unconfirmed_wallet_balance.set(self.root.btc_wallet.unconfirmed_wallet_balance / self.unit_factor)
        self.price.set(self.root.btc_wallet.price)
        self.fiat_wallet_balance.set(f2s(self.root.btc_wallet.fiat_wallet_balance, places=2))
        self.unconfirmed_fiat_wallet_balance.set(f2s(self.root.btc_wallet.unconfirmed_fiat_wallet_balance, places=2))

        # setting low, med, high priority fees
        for i, var in enumerate(self.estimated_fees):
            var.set(self.root.btc_wallet.estimated_fees[i])

        self.next_receiving_address.set(self.root.btc_wallet.receiving_addresses[0])

        updater_thread = self.root.btc_wallet.updater_thread
        status_enum = updater_thread.ApiConnectionStatus
        timestamp = updater_thread.connection_timestamp

        if updater_thread.connection_status == status_enum.first_attempt:
            status = 'API Connection Status: Connecting...'

        elif updater_thread.connection_status == status_enum.error:
            status = f'API Connection Status: Last API call failed'

        elif updater_thread.connection_status == status_enum.good:
            time_str = utils.datetime_str_from_timestamp(timestamp,
                                                         fmt="%H:%M:%S",
                                                         utc=not config.get("USE_LOCALTIME"))
            status = f'API Connection Status: Updated at {time_str}'

        else:
            status = 'Error: Unable to retrieve API status'

        self.api_thread_status.set(status)

        self.root.after(self.refresh_data_rate, self._refresh_data)

    def _about_window(self):
        toplevel = self.root.get_toplevel(self)
        toplevel.grab_set()

        frame = ttk.Frame(toplevel, padding=10)

        author_label = ttk.Label(frame, text='Author:', font=self.root.small_font + ('bold',))
        author_label.grid(row=0, column=0, padx=5, pady=5, sticky='w')

        author = ttk.Label(frame, text='Gavin Shaughnessy', font=self.root.small_font)
        author.grid(row=0, column=1)

        license_label = ttk.Label(frame, text='License:', font=self.root.small_font + ('bold',))
        license_label.grid(row=1, column=0, padx=5, pady=5, sticky='w')

        license_ = ttk.Label(frame, text='GNU GPL v3', font=self.root.small_font)
        license_.grid(row=1, column=1)

        python_ver_label = ttk.Label(frame, text='Python Version:', font=self.root.small_font + ('bold',))
        python_ver_label.grid(row=2, column=0, padx=5, pady=5, sticky='w')

        python_ver = ttk.Label(frame, text='.'.join(str(sys.version_info[i]) for i in range(3)),
                               font=self.root.small_font)
        python_ver.grid(row=2, column=1)

        bitstore_ver_label = ttk.Label(frame, text='Bit-Store Version:', font=self.root.small_font + ('bold',))
        bitstore_ver_label.grid(row=3, column=0, padx=5, pady=5, sticky='w')

        bitstore_ver = ttk.Label(frame, text=config.VERSION, font=self.root.small_font)
        bitstore_ver.grid(row=3, column=1)

        ok_button = ttk.Button(frame, text='OK', command=toplevel.destroy)
        ok_button.grid(row=4, column=0, pady=(10, 0), columnspan=2)

        frame.grid(sticky='nsew')

    def _mnemonic_window(self):
        password = self.root.password_prompt(self)
        if not password:
            return

        try:
            mnemonic = self.root.btc_wallet.get_mnemonic(password)

        except data.IncorrectPasswordError:
            self.root.incorrect_password_prompt(self)
            return

        if mnemonic == '':
            messagebox.showerror('Error', 'Wallet created from BIP32 extended key import.')
            return

        toplevel = self.root.get_toplevel(self)
        toplevel.grab_set()

        frame = ttk.Frame(toplevel)

        title = ttk.Label(frame, text='Mnemonic:', font=self.root.bold_title_font)
        title.grid(row=0, column=0, pady=(20, 10), padx=20)

        info_label = ttk.Label(frame, text='Keep this phrase in a safe place. '
                                           'It can be used to recover and spend '
                                           'all bitcoin in this wallet.',
                               font=self.root.small_font, wrap=350, justify=tk.CENTER)
        info_label.grid(row=1, column=0, pady=5, padx=20)

        mnemonic_label = ttk.Label(frame, text=mnemonic, font=('Courier New', 14, 'bold'),
                                   wrap=350, justify=tk.CENTER)
        mnemonic_label.grid(row=2, column=0, pady=10, padx=20)

        frame.grid(row=0, column=0, sticky='nsew')

        ok_button = ttk.Button(toplevel, text='OK', command=toplevel.destroy)
        ok_button.grid(row=1, column=0, pady=(0, 10), columnspan=2)

    def _info_window(self):
        toplevel = self.root.get_toplevel(self, resizable=False)
        toplevel.grab_set()

        _mxpub = self.root.btc_wallet.xpub
        _axpub = self.root.btc_wallet.account_xpub
        _path = self.root.btc_wallet.path
        _gap_limit = self.root.btc_wallet.gap_limit

        frame = ttk.Frame(toplevel, padding=10)

        note_label = ttk.Label(toplevel, text='Note: Use the "Account XPUB" '
                                              'to create a watch-only version of this wallet',
                               font=self.root.small_font + ('bold',))
        note_label.grid(row=0, column=0, pady=(10, 0))

        master_xpub_label = ttk.Label(frame, text='Master XPUB:', font=self.root.tiny_font)
        master_xpub_label.grid(row=0, column=0, padx=10, sticky='w')

        master_xpub = tk.Text(frame, height=2, font=self.root.tiny_font)
        master_xpub.insert(tk.END, _mxpub)
        master_xpub['state'] = tk.DISABLED
        master_xpub.grid(row=0, column=1, pady=5)

        account_xpub_label = ttk.Label(frame, text='Account XPUB:', font=self.root.tiny_font)
        account_xpub_label.grid(row=1, column=0, padx=10, sticky='w')

        account_xpub = tk.Text(frame, height=2, font=self.root.tiny_font)
        account_xpub.insert(tk.END, _axpub)
        account_xpub['state'] = tk.DISABLED
        account_xpub.grid(row=1, column=1, pady=5)

        path_label = ttk.Label(frame, text='Derivation Path:', font=self.root.tiny_font)
        path_label.grid(row=2, column=0, padx=10, sticky='w')

        path = tk.Text(frame, height=1, font=self.root.tiny_font)
        path.insert(tk.END, _path)
        path['state'] = tk.DISABLED
        path.grid(row=2, column=1, pady=5)

        gap_limit_label = ttk.Label(frame, text='Gap Limit:', font=self.root.tiny_font)
        gap_limit_label.grid(row=3, column=0, padx=10, sticky='w')

        gap_limit = tk.Text(frame, height=1, font=self.root.tiny_font)
        gap_limit.insert(tk.END, _gap_limit)
        gap_limit['state'] = tk.DISABLED
        gap_limit.grid(row=3, column=1, pady=5)

        frame.grid(row=1, column=0, sticky='nsew')

        ok_button = ttk.Button(toplevel, text='OK', command=toplevel.destroy)
        ok_button.grid(row=2, column=0, pady=(0, 10), columnspan=2)


class TransactionView:

    def __init__(self, main_wallet,  txn_data):
        self.root = main_wallet.root
        bold_font = self.root.tiny_font + ('bold',)
        normal_font = self.root.tiny_font
        self.main_wallet = main_wallet

        self.toplevel = self.root.get_toplevel(main_wallet)
        self.frame = ttk.Frame(self.toplevel, padding=10)

        # structs.TransactionData object
        self.txn_data = txn_data

        self.txid_label = ttk.Label(self.frame, text='TXID:', font=bold_font)
        self.txid_label.grid(row=0, column=0, pady=5, padx=5, sticky='w')

        self.txid = tk.Text(self.frame, height=1, font=normal_font)
        self.txid.insert(tk.END, self.txn_data.txid)
        self.txid['state'] = tk.DISABLED
        self.txid.grid(row=0, column=1)

        self.date_label = ttk.Label(self.frame, text='Date:', font=bold_font)
        self.date_label.grid(row=1, column=0, pady=5, padx=5, sticky='w')

        self.date = tk.Text(self.frame, height=1, font=normal_font)
        self.date.insert(tk.END, self.txn_data.date)
        self.date['state'] = tk.DISABLED
        self.date.grid(row=1, column=1)

        self.block_height_label = ttk.Label(self.frame, text='Block Height:', font=bold_font)
        self.block_height_label.grid(row=2, column=0, pady=5, padx=5, sticky='w')

        self.block_height = tk.Text(self.frame, height=1, font=normal_font)
        self.block_height.insert(tk.END, str(self.txn_data.block_height))
        self.block_height['state'] = tk.DISABLED
        self.block_height.grid(row=2, column=1)

        self.confirmations_label = ttk.Label(self.frame, text='Confirmations:', font=bold_font)
        self.confirmations_label.grid(row=3, column=0, pady=5, padx=5, sticky='w')

        self.confirmations = tk.Text(self.frame, height=1, font=normal_font)
        self.confirmations.insert(tk.END, str(self.txn_data.confirmations))
        self.confirmations['state'] = tk.DISABLED
        self.confirmations.grid(row=3, column=1)

        self.fee_label = ttk.Label(self.frame, text='Fee (total):', font=bold_font)
        self.fee_label.grid(row=4, column=0, pady=5, padx=5, sticky='w')

        self.fee = tk.Text(self.frame, height=1, font=normal_font)
        wallet_unit_fee = utils.float_to_str(main_wallet.to_wallet_units(txn_data.fee, "sat"))
        fee_str = f'{wallet_unit_fee} {main_wallet.display_units}'
        self.fee.insert(tk.END, fee_str)
        self.fee['state'] = tk.DISABLED
        self.fee.grid(row=4, column=1)

        self.sat_byte_label = ttk.Label(self.frame, text='Fee (sat/byte):', font=bold_font)
        self.sat_byte_label.grid(row=5, column=0, pady=5, padx=5, sticky='w')

        self.sat_byte = tk.Text(self.frame, height=1, font=normal_font)
        _sat_byte = round(self.txn_data.fee / self.txn_data.vsize, 2)
        self.sat_byte.insert(tk.END, _sat_byte)
        self.sat_byte['state'] = tk.DISABLED
        self.sat_byte.grid(row=5, column=1)

        self.size_label = ttk.Label(self.frame, text='Size (bytes):', font=bold_font)
        self.size_label.grid(row=6, column=0, pady=5, padx=5, sticky='w')

        self.size = tk.Text(self.frame, height=1, font=normal_font)
        self.size.insert(tk.END, str(self.txn_data.vsize))
        self.size['state'] = tk.DISABLED
        self.size.grid(row=6, column=1)

        self.wallet_change_label = ttk.Label(self.frame, text='Wallet Change:', font=bold_font)
        self.wallet_change_label.grid(row=7, column=0, pady=5, padx=5, sticky='w')

        self.wallet_change = tk.Text(self.frame, height=1, font=normal_font)
        _wallet_change = main_wallet.to_wallet_units(self.txn_data.wallet_amount, 'sat')
        str_wallet_change = utils.float_to_str(_wallet_change, show_plus_sign=True)
        self.wallet_change.insert(tk.END, f'{str_wallet_change} {main_wallet.display_units}')
        self.wallet_change['state'] = tk.DISABLED
        self.wallet_change.grid(row=7, column=1)

        self.input_label = ttk.Label(self.frame, text='Inputs:', font=bold_font)
        self.input_label.grid(row=8, column=0, padx=5, sticky='w')

        # addresses that are in the wallet will be highlighted in the fill_ methods
        self.input_text = tk.Text(self.frame, height=5, font=normal_font)
        self.fill_inputs()
        self.input_text['state'] = tk.DISABLED
        self.input_text.grid(row=8, column=1, pady=5)

        self.output_label = ttk.Label(self.frame, text='Outputs:', font=bold_font)
        self.output_label.grid(row=9, column=0, padx=5, sticky='w')

        self.output_text = tk.Text(self.frame, height=5, font=normal_font)
        self.fill_outputs()
        self.output_text['state'] = tk.DISABLED
        self.output_text.grid(row=9, column=1, pady=5)

        self.frame.grid(sticky='nsew')

        self.ok_button = ttk.Button(self.toplevel, text='OK', command=self.toplevel.destroy)
        self.ok_button.grid(pady=(0, 10))

    def is_wallet_address(self, address):
        return address in self.root.btc_wallet.all_addresses

    @staticmethod
    def highlight_strings(text, str_list, colour):
        # highlights all occurrences of the strings in str_list
        for s in str_list:
            # use while True to highlight all occurrences of the string
            start = '1.0'
            while True:
                start_pos = text.search(s, start, stopindex=tk.END)

                if not start_pos:
                    break

                # adding indexes in Text widget...
                end_pos = '{}+{}c'.format(start_pos, len(s))

                text.tag_add('highlight', start_pos, end_pos)
                text.tag_config('highlight', background=colour)

                # start again omitting first char of string so it will find next address
                start = end_pos

    def fill_inputs(self):
        wallet_addrs = []
        for i in self.txn_data.inputs:
            value = utils.float_to_str(self.main_wallet.to_wallet_units(i['value'], 'sat'))
            self.input_text.insert(tk.END, f"{i['address']}    {value} {self.main_wallet.display_units}\n")

            if self.is_wallet_address(i['address']):
                wallet_addrs.append(i['address'])

        self.highlight_strings(self.input_text, wallet_addrs, colour='spring green')

    def fill_outputs(self):
        wallet_addrs = []
        for o in self.txn_data.outputs:
            value = utils.float_to_str(self.main_wallet.to_wallet_units(o['value'], 'sat'))
            self.output_text.insert(tk.END, f"{o['address']}    {value} {self.main_wallet.display_units}\n")

            if self.is_wallet_address(o['address']):
                wallet_addrs.append(o['address'])

        self.highlight_strings(self.output_text, wallet_addrs, colour='spring green')


class WatchOnlyMainWallet(MainWallet):

    def gui_draw(self):
        super().gui_draw()

        self.title_label.config(text=self.root.btc_wallet.name + ' [WATCH-ONLY]')

        send_idx = 1  # index of send_display in self.notebook
        self.notebook.forget(self.send_display)
        self.send_display = WatchOnlySendDisplay(self.notebook, self)
        self.notebook.insert(send_idx, self.send_display, text='Send', underline=0)

        self.wallet_menu.entryconfig('Display Mnemonic', state=tk.DISABLED)


class WatchOnlySendDisplay(SendDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.send_button.destroy()
