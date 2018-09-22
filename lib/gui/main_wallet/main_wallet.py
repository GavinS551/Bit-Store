import tkinter as tk
from tkinter import ttk, messagebox

import datetime

from ._tx_display import TransactionDisplay
from ._send_display import SendDisplay
from ._receive_display import ReceiveDisplay
from ._console_display import ConsoleDisplay

from ...core import config


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame, padding=5)

        self.refresh_data_rate = 1000  # milliseconds

        self.display_units = config.BTC_UNITS
        self.unit_factor = config.UNIT_FACTORS[self.display_units]
        self.max_decimal_places = config.UNITS_MAX_DECIMAL_PLACES[self.display_units]

        # defined in gui_draw
        self.notebook = None
        self.tx_display = None
        self.send_display = None
        self.receive_display = None
        self.console_display = None
        self.title_label = None

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
        menu_bar = tk.Menu(self.root)

        wallet_menu = tk.Menu(menu_bar, tearoff=0)
        wallet_menu.add_command(label='Information')
        wallet_menu.add_separator()
        wallet_menu.add_command(label='Show Mnemonic')
        wallet_menu.add_command(label='Change Password', command=self._change_password_window)

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

            if not new_password_entry.get() == new_password_confirm_entry.get():
                tk.messagebox.showerror('Password Validation', 'New password entries do not match, try again.')
                incorrect = True

            if '' in (new_password_entry.get(), new_password_confirm_entry.get()):
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
            status = (f'API Connection Status: Updated at ' 
                      f'{datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")}')

        else:
            status = 'Error: Unable to retrieve API status'

        self.api_thread_status.set(status)

        self.root.after(self.refresh_data_rate, self._refresh_data)


class WatchOnlyMainWallet(MainWallet):

    def gui_draw(self):
        super().gui_draw()

        self.title_label.config(text=self.root.btc_wallet.name + ' [WATCH-ONLY]')

        send_idx = 1  # index of send_display in self.notebook
        self.notebook.forget(self.send_display)
        self.send_display = WatchOnlySendDisplay(self.notebook, self)
        self.notebook.insert(send_idx, self.send_display, text='Send')


class WatchOnlySendDisplay(SendDisplay):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.send_button.configure(text='Export Txn', command=self.export_txn)
