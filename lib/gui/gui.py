import tkinter as tk
from tkinter import ttk, messagebox

import os
from dataclasses import dataclass
from typing import Any

from . import ttk_simpledialog as simpledialog
from .. import wallet, config, bip32

from ..exceptions.data_exceptions import IncorrectPasswordError
from ..exceptions.gui_exceptions import *


ICON = os.path.join(os.path.dirname(__file__), 'assets', 'bc_logo.ico')


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
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        # starting frame
        self.show_frame(WalletSelect)

        # init will be done in other frames, this is a placeholder
        self.btc_wallet = None

    def show_frame(self, frame):
        f = self.frames[frame]
        f.gui_draw()
        f.tkraise()
        self.update_idletasks()

    def wallet_init(self, name, password):
        self.btc_wallet = wallet.Wallet(name=name, password=password)

    def password_prompt(self):
        return TTKSimpleDialog.askstring('Password Entry', 'Enter Password:',
                                         show='*', parent=self.master_frame)


class Settings(tk.Toplevel):

    def __init__(self, root):
        tk.Toplevel.__init__(self, root.master_frame)
        self.wm_title('Settings')
        self.wm_iconbitmap(ICON)

        self.frame = ttk.Frame()
        self.frame.pack(expand=True)


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

    def gui_draw(self):
        title_label = ttk.Label(self, text=self.root.btc_wallet.name,
                                font=self.root.bold_title_font)
        title_label.grid(row=0, column=0)


class WalletSelect(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        # attributes below will be defined in gui_draw() method
        self.wallet_list = None

    def gui_draw(self):
        title_label = ttk.Label(self, text='Select Wallet:',
                                font=self.root.bold_title_font)
        title_label.grid(row=0, column=0, sticky='n', pady=5)

        self.wallet_list = tk.Listbox(self, width=30, height=10, font=self.root.title_font)

        # fill wallet_list with all wallets
        for i, w in enumerate(self.wallets):
            self.wallet_list.insert(i, w)

        # make a create wallet option if there are no wallets
        if not self.wallets:
            self.wallet_list.insert(0, '<NEW WALLET>')

        self.wallet_list.grid(row=1, column=0, pady=10, padx=10, rowspan=3)

        scroll_bar = ttk.Scrollbar(self)
        scroll_bar.grid(row=1, column=1, rowspan=3, sticky='nsw')
        scroll_bar.config(command=self.wallet_list.yview)

        self.wallet_list.config(yscrollcommand=scroll_bar.set)

        options_frame = ttk.Frame(self)
        options_frame.grid(row=1, column=2)

        options_label = ttk.Label(options_frame, text='Options:',
                                  font=self.root.bold_title_font)
        options_label.grid(row=0, column=0, padx=10)

        select_button = ttk.Button(options_frame, text='Select Wallet',
                                   command=self.select_wallet)
        select_button.grid(row=1, column=0, pady=20, sticky='ew')

        # binds a double click on listbox to trigger same method as button
        # not sure why this only works with a lambda and one arg...
        self.wallet_list.bind('<Double-1>', lambda x: self.select_wallet())

        new_wallet_button = ttk.Button(options_frame, text='New Wallet',
                                       command=lambda: self.root.show_frame(WalletCreation))
        new_wallet_button.grid(row=2, column=0, sticky='ew')

        import_wallet_button = ttk.Button(options_frame, text='Import Wallet')
        import_wallet_button['state'] = tk.DISABLED
        import_wallet_button.grid(row=3, column=0, sticky='ew')

        edit_wallet_button = ttk.Button(options_frame, text='Edit Wallet')
        edit_wallet_button.grid(row=4, column=0, sticky='ew')

        settings_button = ttk.Button(options_frame, text='Settings',
                                     command=lambda: Settings(self.root))
        settings_button.grid(row=5, column=0, pady=20, sticky='ew')

    @property
    def wallets(self):
        # list of all directories in program's DATA_DIR (i.e all wallets)
        return [w for w in os.listdir(config.DATA_DIR)
                if os.path.isdir(os.path.join(config.DATA_DIR, w))]

    def select_wallet(self):
        try:
            if self.wallet_list.curselection():
                selected_wallet = self.wallet_list.get(tk.ACTIVE)

                # if <CREATE WALLET> is selected, go to wallet creation frame
                if selected_wallet == '<NEW WALLET>':
                    self.root.show_frame(WalletCreation)
                    return

            else:
                raise NoWalletSelectedError

            password = self.root.password_prompt()

            # if the password prompt window is exited without submitting,
            # password will be None and will raise an Exception
            if password is None:
                return

            self.root.wallet_init(name=selected_wallet, password=password)

            self.root.show_frame(MainWallet)

        except (NoWalletSelectedError, IncorrectPasswordError) as ex:
            if isinstance(ex, NoWalletSelectedError):
                messagebox.showerror('Error', 'No wallet selected')

            if isinstance(ex, IncorrectPasswordError):
                messagebox.showerror('Error', 'Incorrect Password')


class WalletCreation(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.grid_columnconfigure(2, {'minsize': 100})

        # attributes below will be defined in gui_draw()
        self.password_entry = None
        self.confirm_pass_entry = None
        self.path_entry = None
        self.segwit_check = None
        self.name_entry = None
        self.mnemonic_passphrase_entry = None

    def gui_draw(self):
        title = ttk.Label(self, text='Wallet Creation:', font=self.root.bold_title_font)
        title.grid(row=0, column=0, sticky='w', pady=10)

        required_label = ttk.Label(self, text=' * Required entries', font=self.root.tiny_font)
        required_label.grid(row=0, column=1)

        name_label = ttk.Label(self, text='Enter Name:*', font=self.root.small_font)
        name_label.grid(row=1, column=0, sticky='w')

        self.name_entry = ttk.Entry(self)
        self.name_entry.grid(row=1, column=1, pady=5, columnspan=2)

        password_label = ttk.Label(self, text='Enter Password:*', font=self.root.small_font)
        password_label.grid(row=2, column=0, sticky='w')

        self.password_entry = ttk.Entry(self, show='*')
        self.password_entry.grid(row=2, column=1, pady=5, columnspan=2)

        confirm_pass_label = ttk.Label(self, text='Confirm Password:*', font=self.root.small_font)
        confirm_pass_label.grid(row=3, column=0, sticky='w')

        self.confirm_pass_entry = ttk.Entry(self, show='*')
        self.confirm_pass_entry.grid(row=3, column=1, pady=5, columnspan=2)

        path_label = ttk.Label(self, text='Custom Path:', font=self.root.small_font)
        path_label.grid(row=4, column=0, sticky='w')

        self.path_entry = ttk.Entry(self)
        self.path_entry.grid(row=4, column=1, pady=5, columnspan=2)

        path_default = ttk.Label(self, text='(Default: 49\'/0\'/0\')', font=self.root.tiny_font)
        path_default.grid(row=4, column=3, padx=5, sticky='w')

        segwit_label = ttk.Label(self, text='Segwit Enabled:', font=self.root.small_font)
        segwit_label.grid(row=5, column=0, sticky='w')

        self.segwit_check = tk.IntVar(value=1)
        segwit_enabled_check = ttk.Checkbutton(self, variable=self.segwit_check)
        segwit_enabled_check.grid(row=5, column=1, pady=5)

        recommend_label = ttk.Label(self, text='(Recommended)', font=self.root.tiny_font)
        recommend_label.grid(row=5, column=3, padx=5, sticky='w')

        mnemonic_passphrase_label = ttk.Label(self, text='Mnemonic Passphrase:', font=self.root.small_font)
        mnemonic_passphrase_label.grid(row=6, column=0, sticky='w')

        self.mnemonic_passphrase_entry = ttk.Entry(self)
        self.mnemonic_passphrase_entry.grid(row=6, column=1, pady=5, columnspan=2)

        back_button = ttk.Button(self, text='Back',
                                 command=lambda: self.root.show_frame(WalletSelect))
        back_button.grid(row=7, column=0, sticky='e', padx=10, pady=20)

        create_button = ttk.Button(self, text='Create', command=self.create_wallet)
        create_button.grid(row=7, column=1, sticky='w', padx=10, pady=20)

    def _verify_password(self):
        return self.password_entry.get() == self.confirm_pass_entry.get()

    # custom mnemonic and xkey params are meant for subclassing this class when
    # implementing wallet import feature
    def create_wallet(self, mnemonic=bip32.Bip32.gen_mnemonic(), xkey=None):
        try:
            name = self.name_entry.get()
            password = self.password_entry.get()

            if self.mnemonic_passphrase_entry.get() is None:
                passphrase = ''
            else:
                passphrase = self.mnemonic_passphrase_entry.get()

            if self.path_entry.get() == '':
                # setting default path
                path = config.BIP32_PATHS['bip49path']
            else:
                path = self.path_entry.get()

            is_segwit = True if self.segwit_check.get() == 1 else False

            # error checking
            if not name:
                raise ValueError('No name entered')

            if not password:
                raise ValueError('No password entered')

            if not self._verify_password():
                self.password_entry.delete(0, 'end')
                self.confirm_pass_entry.delete(0, 'end')
                raise ValueError('Passwords don\'t match')

            if not bip32.Bip32.check_path(path):
                raise ValueError(f'Invalid path entered: ({path})')

            if mnemonic is not None and xkey is not None:
                raise ValueError('Either "mnemonic" or "xkey" arguments must be None')
            elif mnemonic is None and xkey is None:
                raise ValueError('Either "mnemonic" or "xkey" arguments must have a value')

            # show loading frame after all error checks are complete
            self.root.show_frame(WalletCreationLoading)

            @dataclass
            class WalletCreationData:

                name: str
                password: str
                passphrase: str
                is_segwit: bool
                path: str
                mnemonic: Any
                xkey: Any

            wd = WalletCreationData(name, password, passphrase,
                                    is_segwit, path, mnemonic, xkey)

        except Exception as ex:
            tk.messagebox.showerror('Error', f'{ex.__str__()}')

            # if an exception was raised during wallet creation, the frame will
            # have to be re-shown as the loading frame was raised after error-
            # checking entry fields
            self.root.show_frame(WalletCreation)


class WalletCreationLoading(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.grid_rowconfigure(0, {'minsize': 50})
        self.grid_columnconfigure(0, {'minsize': 35})

    def gui_draw(self):
        title = ttk.Label(self, text='Creating Wallet, Please Wait...',
                          font=self.root.bold_title_font)
        title.grid(row=1, column=1, sticky='n')

        loading_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=400, mode='indeterminate')
        loading_bar.grid(row=2, column=1, pady=40, padx=20)
        loading_bar.start()


class WalletCreationShowMnemonic(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

    def gui_draw(self):
        pass


class WalletCreationVerifyMnemonic(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

    def gui_draw(self):
        pass


def main():
    app = RootApplication()
    app.mainloop()
