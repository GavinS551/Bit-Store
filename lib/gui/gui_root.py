import tkinter as tk
from tkinter import ttk, messagebox

import os
import traceback
import platform

from . import ttk_simpledialog as simpledialog
from ..core import config, wallet

from .wallet_select import WalletSelect
from .wallet_creation import (WalletCreation, WalletCreationLoading,
                              WalletCreationShowMnemonic, WalletCreationVerifyMnemonic)
from .main_wallet import MainWallet


def main():
    app = RootApplication()
    app.mainloop()

    # setting event in api_data_updater thread of Wallet instance after
    # tkinter mainloop closes
    if app.btc_wallet is not None:
        app.btc_wallet.updater_thread.event.set()


class TTKSimpleDialog(simpledialog._QueryString):
    """ sub-classed _QueryString that sets the project icon """

    def body(self, master):
        super().body(master)
        self.iconbitmap(RootApplication.ICON)
        self.geometry('250x90')
        self.resizable(False, False)

    @staticmethod
    def askstring(title, prompt, **kwargs):
        d = TTKSimpleDialog(title, prompt, **kwargs)
        return d.result


class RootApplication(tk.Tk):

    ICON = os.path.join(os.path.dirname(__file__), 'assets', 'bc_logo.ico') if platform.system() == 'Windows' else None

    bold_title_font = (config.FONT, 14, 'bold')
    title_font = (config.FONT, 14)
    small_font = (config.FONT, 10)
    tiny_font = (config.FONT, 8)

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.resizable(False, False)

        self.wm_title('Bit-Store')
        self.iconbitmap(self.ICON)
        
        self.style = ttk.Style()
        if platform.system() == 'Linux':
            self.style.theme_use('clam')
        self.set_style()

        self.master_frame = ttk.Frame(self, padding=20)

        self.master_frame.grid_columnconfigure(0, weight=1)
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.pack(expand=True)

        self.frames = {}

        # adding all frames to self.frames dict, and adding them to master_grid
        for f in (WalletSelect, WalletCreation, MainWallet,
                  WalletCreationLoading, WalletCreationShowMnemonic,
                  WalletCreationVerifyMnemonic):

            frame = f(self)
            self.frames[f.__name__] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        # starting frame
        self.show_frame('WalletSelect')

        # init will be done in other frames, this is a placeholder
        # will be a lib.core.wallet Wallet instance acting as the main interface for the gui
        self.btc_wallet = None

    def report_callback_exception(self, exc_type, exc_value, exc_traceback):
        """ this will show an error window in the gui displaying any unhandled exception
         (overridden Tk method)
        """
        message = ''.join(traceback.format_exception(exc_type,
                                                     exc_value,
                                                     exc_traceback))

        error_window = tk.Toplevel(self)
        error_window.bell()
        error_window.wm_iconbitmap(self.ICON)
        error = tk.Text(error_window, font=self.tiny_font, wrap=tk.WORD)
        error.insert(tk.END, message)
        error.pack(expand=True)

    # kwargs is used to pass data into frame objects
    def show_frame(self, frame, **kwargs):
        f = self.frames[frame]

        for k, v in kwargs.items():
            setattr(f, k, v)

        f.gui_draw()
        f.tkraise()
        self.update_idletasks()

    def set_style(self):
        self.style.configure('Treeview.Heading', font=(config.FONT, 10))

    def wallet_init(self, name, password):
        self.btc_wallet = wallet.Wallet(name=name, password=password)

    @staticmethod
    def password_prompt(parent):
        return TTKSimpleDialog.askstring('Password Entry', 'Enter Password:',
                                         show='*', parent=parent)

    @staticmethod
    def incorrect_password_prompt(parent):
        tk.messagebox.showerror('Error', 'Incorrect Password', parent=parent)

    def settings_prompt(self):
        _Settings(self)


class _Settings(tk.Toplevel):

    def __init__(self, root):
        tk.Toplevel.__init__(self, root.master_frame)
        self.wm_title('Settings')
        self.wm_iconbitmap(RootApplication.ICON)

        self.resizable(False, False)
        self.grab_set()

        self.root = root

        # settings variables, set to current values
        self.spend_unconfirmed_outs = tk.BooleanVar(value=config.SPEND_UNCONFIRMED_UTXOS)
        self.spend_utxos_individually = tk.BooleanVar(value=config.SPEND_UTXOS_INDIVIDUALLY)
        self.blockchain_api = tk.StringVar(value=config.BLOCKCHAIN_API_SOURCE)
        self.price_api = tk.StringVar(value=config.PRICE_API_SOURCE)
        self.fiat_unit = tk.StringVar(value=config.FIAT)
        self.btc_units = tk.StringVar(value=config.BTC_UNITS)

        # config variable names as keys with their corresponding tk Variables
        self.config_vars = {
            'SPEND_UNCONFIRMED_UTXOS': self.spend_unconfirmed_outs,
            'SPEND_UTXOS_INDIVIDUALLY': self.spend_utxos_individually,
            'BLOCKCHAIN_API_SOURCE': self.blockchain_api,
            'PRICE_API_SOURCE': self.price_api,
            'FIAT': self.fiat_unit,
            'BTC_UNITS': self.btc_units
        }

        self.notebook = ttk.Notebook(self)

        self.transaction_settings = ttk.Frame(self.notebook, padding=10)
        self.draw_transaction_settings()
        self.transaction_settings.grid(sticky='nsew')
        self.notebook.add(self.transaction_settings, text='Transactions')

        self.api_settings = ttk.Frame(self.notebook, padding=10)
        self.draw_api_settings()
        self.api_settings.grid(sticky='nsew')
        self.notebook.add(self.api_settings, text='API')

        self.gui_settings = ttk.Frame(self.notebook, padding=10)
        self.draw_gui_settings()
        self.gui_settings.grid(sticky='nsew')
        self.notebook.add(self.gui_settings, text='GUI')

        self.notebook.grid(row=0, column=0, padx=20, pady=10)

        save_button = ttk.Button(self, text='Save', command=self.on_save)
        save_button.grid(row=1, column=0, pady=(0, 10), sticky='s')

    def on_save(self):
        new_settings = self._write_config_values()

        self.destroy()

        if new_settings:
            tk.messagebox.showinfo('Settings',
                                   'Please restart the program for these changes to take effect.')

    def _write_config_values(self):
        """ returns False if no data was written (i.e no settings changed),
        otherwise True
        """

        # if no settings were changed
        if all([v.get() == getattr(config, k) for k, v in self.config_vars.items()]):
            return False

        else:
            data = {}
            for k, v in self.config_vars.items():
                data[k] = v.get()

            config.write_values(**data)

            return True

    def draw_transaction_settings(self):
        frame = self.transaction_settings
        padx = (0, 20)

        spend_unconfirmed_outs_label = ttk.Label(frame, text='Spend Unconfirmed Outputs:',
                                                 font=self.root.tiny_font)
        spend_unconfirmed_outs_label.grid(row=0, column=0, padx=padx, pady=10, sticky='w')

        spend_unconfirmed_outs_check = ttk.Checkbutton(frame, variable=self.spend_unconfirmed_outs,
                                                       offvalue=False, onvalue=True)
        spend_unconfirmed_outs_check.grid(row=0, column=1, sticky='e')

        spend_utxos_individually_label = ttk.Label(frame, text='Spend Outputs Individually:',
                                                   font=self.root.tiny_font)
        spend_utxos_individually_label.grid(row=1, column=0, padx=padx, pady=10, sticky='w')

        spend_utxos_individually_check = ttk.Checkbutton(frame, variable=self.spend_utxos_individually,
                                                         offvalue=False, onvalue=True)
        spend_utxos_individually_check.grid(row=1, column=1, sticky='e')

    def draw_api_settings(self):
        frame = self.api_settings
        padx = (0, 20)

        blockchain_api_label = ttk.Label(frame, text='Blockchain API:', font=self.root.tiny_font)
        blockchain_api_label.grid(row=0, column=0, padx=padx, pady=10, sticky='w')

        blockchain_api_options = ttk.Combobox(frame, textvariable=self.blockchain_api,
                                              state='readonly', value=config.POSSIBLE_BLOCKCHAIN_API_SOURCES,
                                              width=15)
        blockchain_api_options.grid(row=0, column=1, sticky='e')

        price_api_label = ttk.Label(frame, text='Price API:', font=self.root.tiny_font)
        price_api_label.grid(row=1, column=0, padx=padx, pady=10, sticky='w')

        price_api_options = ttk.Combobox(frame, textvariable=self.price_api,
                                         state='readonly', value=config.POSSIBLE_PRICE_API_SOURCES,
                                         width=15)
        price_api_options.grid(row=1, column=1, sticky='e')

    def draw_gui_settings(self):
        frame = self.gui_settings
        padx = (0, 58)

        fiat_label = ttk.Label(frame, text='Fiat Currency:', font=self.root.tiny_font)
        fiat_label.grid(row=0, column=0, padx=padx, pady=10, sticky='w')

        fiat_options = ttk.Combobox(frame, textvariable=self.fiat_unit,
                                    state='readonly', value=config.POSSIBLE_FIAT_UNITS, width=10)
        fiat_options.grid(row=0, column=1, sticky='e')

        btc_units_label = ttk.Label(frame, text='Bitcoin Units:', font=self.root.tiny_font)
        btc_units_label.grid(row=1, column=0, padx=padx, pady=10, sticky='w')

        btc_units_options = ttk.Combobox(frame, textvariable=self.btc_units,
                                         state='readonly', value=config.POSSIBLE_BTC_UNITS, width=10)
        btc_units_options.grid(row=1, column=1, sticky='e')
