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

from ...core import config, utils, data


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame, padding=5)

        self.refresh_data_rate = 1000  # milliseconds

        self.display_units = config.get_value('BTC_UNITS')
        self.unit_factor = config.UNIT_FACTORS[self.display_units]
        self.max_decimal_places = config.UNITS_MAX_DECIMAL_PLACES[self.display_units]

        # defined in gui_draw
        self.notebook = None
        self.tx_display = None
        self.send_display = None
        self.receive_display = None
        self.console_display = None
        self.title_label = None

        self.menu_bar = None
        self.wallet_menu = None
        self.options_menu = None

        # attributes below will be updated in _refresh_data method
        self.wallet_balance = tk.DoubleVar()
        self.unconfirmed_wallet_balance = tk.DoubleVar()
        self.price = tk.DoubleVar()
        self.fiat_wallet_balance = tk.DoubleVar()
        self.unconfirmed_fiat_wallet_balance = tk.DoubleVar()

        self.next_receiving_address = tk.StringVar()

        self.api_thread_status = tk.StringVar()

    def gui_draw(self):

        self.title_label = ttk.Label(self, text=self.root.btc_wallet.name,
                                     font=self.root.bold_title_font)
        self.title_label.grid(row=0, column=0)

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

        self.console_display = ConsoleDisplay(self.notebook, self)
        self.console_display.grid(sticky='nsew')
        self.notebook.add(self.console_display, text='Console', underline=0)

        self.notebook.grid(row=1, column=0, pady=(0, 10))

        self._draw_bottom_info_bar()
        self._draw_menu_bar()
        self._draw_api_status()
        self._refresh_data()

    def _draw_menu_bar(self):
        self.menu_bar = tk.Menu(self.root)

        self.wallet_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.wallet_menu.add_command(label='Information', command=self._info_window)
        self.wallet_menu.add_separator()
        self.wallet_menu.add_command(label='Display Mnemonic', command=self._mnemonic_window)
        self.wallet_menu.add_command(label='Change Password', command=self._change_password_window)

        self.options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.options_menu.add_command(label='Settings', command=self.root.settings_prompt)

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
        fiat_balance_label = ttk.Label(fiat_balance_frame, text=f'{config.get_value("FIAT")} Balance:',
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

        change_pass_window = tk.Toplevel(self)
        change_pass_window.iconbitmap(self.root.ICON)
        change_pass_window.resizable(False, False)
        change_pass_window.grab_set()

        def on_ok():
            incorrect = False
            if not data_store.validate_password(old_password_entry.get()):
                tk.messagebox.showerror('Incorrect Password', 'Old Password is incorrect, try again.')
                incorrect = True

            elif not new_password_entry.get() == new_password_confirm_entry.get():
                tk.messagebox.showerror('Password Validation', 'New password entries do not match, try again.')
                incorrect = True

            elif '' in (new_password_entry.get(), new_password_confirm_entry.get()):
                tk.messagebox.showerror('Blank Password', 'Password cannot be blank')
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

        old_password_label = ttk.Label(change_pass_frame, text='Old Password:',
                                       font=self.root.small_font)
        old_password_label.grid(row=0, column=0, pady=5, padx=10, sticky='w')

        old_password_entry = ttk.Entry(change_pass_frame, show='*')
        old_password_entry.grid(row=0, column=1)

        new_password_label = ttk.Label(change_pass_frame, text='New Password:',
                                       font=self.root.small_font)
        new_password_label.grid(row=1, column=0, pady=5, padx=10, sticky='w')

        new_password_entry = ttk.Entry(change_pass_frame, show='*')
        new_password_entry.grid(row=1, column=1)

        new_password_confirm_label = ttk.Label(change_pass_frame, text='Confirm Password:',
                                               font=self.root.small_font)
        new_password_confirm_label.grid(row=2, column=0, pady=5, padx=10, sticky='w')

        new_password_confirm_entry = ttk.Entry(change_pass_frame, show='*')
        new_password_confirm_entry.grid(row=2, column=1)

        enter_button = ttk.Button(change_pass_frame, text='OK', command=on_ok)
        enter_button.grid(row=3, column=0, padx=10, pady=(10, 0), sticky='e')

        cancel_button = ttk.Button(change_pass_frame, text='Cancel', command=on_cancel)
        cancel_button.grid(row=3, column=1, padx=10, pady=(10, 0), sticky='w')

        change_pass_frame.grid(sticky='nsew')

    def _refresh_data(self):
        self.wallet_balance.set(self.root.btc_wallet.wallet_balance / self.unit_factor)
        self.unconfirmed_wallet_balance.set(self.root.btc_wallet.unconfirmed_wallet_balance / self.unit_factor)
        self.price.set(self.root.btc_wallet.price)
        self.fiat_wallet_balance.set(self.root.btc_wallet.fiat_wallet_balance)
        self.unconfirmed_fiat_wallet_balance.set(self.root.btc_wallet.unconfirmed_fiat_wallet_balance)

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
                                                         utc=not config.get_value("USE_LOCALTIME"))
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

        python_ver = ttk.Label(frame, text='.'.join(str(sys.version_info[i]) for i in range(3)))
        python_ver.grid(row=2, column=1)

        ok_button = ttk.Button(frame, text='OK', command=toplevel.destroy)
        ok_button.grid(row=3, column=0, pady=(10, 0), columnspan=2)

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
        master_xpub_label.grid(row=0, column=0, pady=10, padx=10, sticky='w')

        master_xpub = tk.Text(frame, height=2, font=self.root.tiny_font)
        master_xpub.insert(tk.END, _mxpub)
        master_xpub['state'] = tk.DISABLED
        master_xpub.configure(inactiveselectbackground=master_xpub.cget("selectbackground"))
        master_xpub.grid(row=0, column=1)

        account_xpub_label = ttk.Label(frame, text='Account XPUB:', font=self.root.tiny_font)
        account_xpub_label.grid(row=1, column=0, pady=10, padx=10, sticky='w')

        account_xpub = tk.Text(frame, height=2, font=self.root.tiny_font)
        account_xpub.insert(tk.END, _axpub)
        account_xpub['state'] = tk.DISABLED
        account_xpub.configure(inactiveselectbackground=account_xpub.cget("selectbackground"))
        account_xpub.grid(row=1, column=1)

        path_label = ttk.Label(frame, text='Derivation Path:', font=self.root.tiny_font)
        path_label.grid(row=2, column=0, pady=5, padx=10, sticky='w')

        path = tk.Text(frame, height=1, font=self.root.tiny_font)
        path.insert(tk.END, _path)
        path['state'] = tk.DISABLED
        path.configure(inactiveselectbackground=path.cget("selectbackground"))
        path.grid(row=2, column=1)

        gap_limit_label = ttk.Label(frame, text='Gap Limit:', font=self.root.tiny_font)
        gap_limit_label.grid(row=3, column=0, pady=5, padx=10, sticky='w')

        gap_limit = tk.Text(frame, height=1, font=self.root.tiny_font)
        gap_limit.insert(tk.END, _gap_limit)
        gap_limit['state'] = tk.DISABLED
        gap_limit.configure(inactiveselectbackground=gap_limit.cget("selectbackground"))
        gap_limit.grid(row=3, column=1)

        frame.grid(row=1, column=0, sticky='nsew')

        ok_button = ttk.Button(toplevel, text='OK', command=toplevel.destroy)
        ok_button.grid(row=2, column=0, pady=(0, 10), columnspan=2)


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
