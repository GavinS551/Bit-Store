import tkinter as tk
from tkinter import ttk, messagebox

import os

from .. import config


class WalletSelect(ttk.Frame):

    def __init__(self, root):
        ttk.Frame.__init__(self, root.master_frame)

        self.title_label = ttk.Label(self, text='Select Wallet:', font=(config.FONT, 14, 'bold'))
        self.title_label.grid(row=0, column=0, sticky='n', pady=5)

        self.wallet_list = tk.Listbox(self, font=(config.FONT, 14))
        for i, w in enumerate(self.wallets):
            self.wallet_list.insert(i, w)

        self.wallet_list.grid(row=1, column=0, pady=10, padx=10, rowspan=3)

        self.scroll_bar = ttk.Scrollbar(self)
        self.scroll_bar.grid(row=1, column=1, rowspan=3, sticky='nsw')
        self.scroll_bar.config(command=self.wallet_list.yview)

        self.wallet_list.config(yscrollcommand=self.scroll_bar.set)

        self.options_frame = ttk.Frame(self)
        self.options_frame.grid(row=1, column=2)

        self.options_label = ttk.Label(self.options_frame, text='Options:', font=(config.FONT, 14, 'bold'))
        self.options_label.grid(row=0, column=0, padx=10)

        self.select_button = ttk.Button(self.options_frame, text='Select Wallet', command=self.select_wallet)
        self.select_button.grid(row=1, column=0, pady=20)

        self.new_wallet_button = ttk.Button(self.options_frame, text='New Wallet')
        self.new_wallet_button.grid(row=2, column=0)

        self.rename_wallet = ttk.Button(self.options_frame, text='Edit Wallet')
        self.rename_wallet.grid(row=3, column=0)

        self.settings = ttk.Button(self.options_frame, text='Settings')
        self.settings.grid(row=4, column=0, pady=20)

    @property
    def wallets(self):
        # list of all directories in program's DATA_DIR (i.e all wallets)
        return [w for w in os.listdir(config.DATA_DIR) if os.path.isdir(os.path.join(config.DATA_DIR, w))]

    def select_wallet(self):
        try:
            wallet = self.wallets[self.wallet_list.curselection()[0]]
        except IndexError:
            messagebox.showinfo('Error', 'No wallet selected!')
