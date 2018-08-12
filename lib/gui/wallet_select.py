import tkinter as tk
from tkinter import ttk, messagebox

import os

from lib.core import config

from ..exceptions.data_exceptions import IncorrectPasswordError
from ..exceptions.gui_exceptions import *


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
        select_button.grid(row=1, column=0, pady=20, padx=5, sticky='ew')

        # binds a double click on listbox to trigger same method as button
        self.wallet_list.bind('<Double-1>', lambda x: self.select_wallet())

        new_wallet_button = ttk.Button(options_frame, text='New Wallet',
                                       command=lambda: self.root.show_frame('WalletCreation'))
        new_wallet_button.grid(row=2, column=0, padx=5, sticky='ew')

        import_wallet_button = ttk.Button(options_frame, text='Import Wallet')
        import_wallet_button['state'] = tk.DISABLED
        import_wallet_button.grid(row=3, column=0, padx=5, sticky='ew')

        edit_wallet_button = ttk.Button(options_frame, text='Edit Wallet')
        edit_wallet_button.grid(row=4, column=0, padx=5, sticky='ew')

        settings_button = ttk.Button(options_frame, text='Settings',
                                     command=self.root.settings_prompt)
        settings_button.grid(row=5, column=0, pady=20, padx=5, sticky='ew')

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
                    self.root.show_frame('WalletCreation')
                    return

            else:
                raise NoWalletSelectedError

            password = self.root.password_prompt()

            # if the password prompt window is exited without submitting,
            # password will be None and will raise an Exception
            if password is None:
                return

            self.root.wallet_init(name=selected_wallet, password=password)

            self.root.show_frame('MainWallet')

        except (NoWalletSelectedError, IncorrectPasswordError) as ex:
            if isinstance(ex, NoWalletSelectedError):
                messagebox.showerror('Error', 'No wallet selected')

            if isinstance(ex, IncorrectPasswordError):
                messagebox.showerror('Error', 'Incorrect Password')
