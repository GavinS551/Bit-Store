import tkinter as tk
from tkinter import ttk

import os
import traceback

from . import ttk_simpledialog as simpledialog
from ..core import config, wallet

from .wallet_select import WalletSelect
from .wallet_creation import (WalletCreation, WalletCreationLoading,
                              WalletCreationShowMnemonic, WalletCreationVerifyMnemonic)
from .main_wallet import MainWallet


ICON = os.path.join(os.path.dirname(__file__), 'assets', 'bc_logo.ico')


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
        self.iconbitmap(ICON)
        self.geometry('250x90')
        self.resizable(False, False)

    @staticmethod
    def askstring(title, prompt, **kwargs):
        d = TTKSimpleDialog(title, prompt, **kwargs)
        return d.result


class RootApplication(tk.Tk):

    bold_title_font = (config.FONT, 14, 'bold')
    title_font = (config.FONT, 14)
    small_font = (config.FONT, 10)
    tiny_font = (config.FONT, 8)

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.wm_title('Bit-Store')
        self.iconbitmap(ICON)
        self.style = ttk.Style()
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
        error_window.wm_iconbitmap(ICON)
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

    def password_prompt(self):
        return TTKSimpleDialog.askstring('Password Entry', 'Enter Password:',
                                         show='*', parent=self.master_frame)

    def settings_prompt(self):
        _Settings(self)


class _Settings(tk.Toplevel):

    def __init__(self, root):
        tk.Toplevel.__init__(self, root.master_frame)
        self.wm_title('Settings')
        self.wm_iconbitmap(ICON)

        self.notebook = ttk.Notebook(self)

        self.transaction_settings = ttk.Frame(self.notebook)
        self.draw_transaction_settings()
        self.transaction_settings.grid(sticky='nsew')
        self.notebook.add(self.transaction_settings, text='Transactions')

        self.api_settings = ttk.Frame(self.notebook)
        self.draw_api_settings()
        self.api_settings.grid(sticky='nsew')
        self.notebook.add(self.api_settings, text='API')

        self.gui_settings = ttk.Frame(self.notebook)
        self.draw_gui_settings()
        self.gui_settings.grid(sticky='nsew')
        self.notebook.add(self.gui_settings, text='GUI')

        self.notebook.grid(padx=20, pady=20)

    def draw_transaction_settings(self):
        pass

    def draw_api_settings(self):
        pass

    def draw_gui_settings(self):
        pass
