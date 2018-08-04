import tkinter as tk
from tkinter import ttk, messagebox

import threading
from dataclasses import dataclass
from typing import Any

from .. import bip32, config, wallet


def threaded(func):

    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        t.start()
        return t

    return wrapper


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
                                 command=lambda: self.root.show_frame('WalletSelect'))
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

            if not None in [mnemonic, xkey]:
                raise ValueError('Either "mnemonic" or "xkey" arguments must be None')
            elif all(x is None for x in [mnemonic, xkey]):
                raise ValueError('Either "mnemonic" or "xkey" arguments must have a value')

            # show loading frame after all error checks are complete
            self.root.show_frame('WalletCreationLoading')

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

            self._build_wallet_instance_thread(wd)

        except ValueError as ex:
            messagebox.showerror('Error', f'{ex.__str__()}')

            # if an exception was raised during wallet creation, the frame will
            # have to be re-shown as the loading frame was raised after error-
            # checking entry fields
            self.root.show_frame('WalletCreation')

    @threaded
    def _build_wallet_instance_thread(self, wallet_data):
        if wallet_data.xkey is None:
            bip32_ = bip32.Bip32.from_mnemonic(wallet_data.mnemonic,
                                               wallet_data.path,
                                               wallet_data.passphrase,
                                               wallet_data.is_segwit)
        else:
            bip32_ = bip32.Bip32(wallet_data.xkey,
                                 wallet_data.path,
                                 wallet_data.is_segwit)

        w = wallet.Wallet.new_wallet(wallet_data.name, wallet_data.password, bip32_)
        self.root.btc_wallet = w
        self.root.show_frame('WalletCreationShowMnemonic')


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
