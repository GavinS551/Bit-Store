import tkinter as tk
from tkinter import ttk, messagebox

import os

from .. import wallet, config


ICON = os.path.join(os.path.dirname(__file__), 'assets', 'bc_logo.ico')


class MainApplication(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.wm_title('Bit-Store')
        self.iconbitmap(ICON)

        self.master_frame = ttk.Frame(self)

        self.master_frame.grid_columnconfigure(0, weight=1)
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.grid(row=0, column=0, sticky='nsew')

        self.frames = {}

        # adding all frames to self.frames dict, and adding them to master_grid
        for f in (WalletSelect, WalletCreation):
            frame = f(self)
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        # starting frame
        self.show_frame(WalletSelect)

        # init will be done in WalletSelect class, this is a placeholder
        self.btc_wallet = wallet.Wallet

    def show_frame(self, frame):
        self.frames[frame].tkraise()
        self.update_idletasks()


class Settings(tk.Toplevel):

    def __init__(self, root):
        tk.Toplevel.__init__(self, root.master_frame)
        self.wm_title('Settings')
        self.wm_iconbitmap(ICON)


class WalletSelect(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.title_label = ttk.Label(self, text='Select Wallet:',
                                     font=(config.FONT, 14, 'bold'))
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

        self.options_label = ttk.Label(self.options_frame, text='Options:',
                                       font=(config.FONT, 14, 'bold'))
        self.options_label.grid(row=0, column=0, padx=10)

        self.select_button = ttk.Button(self.options_frame, text='Select Wallet',
                                        command=self.select_wallet)
        self.select_button.grid(row=1, column=0, pady=20)

        # binds a double click on listbox to trigger select_button
        self.wallet_list.bind('<Double-1>', self.select_button.invoke)

        self.new_wallet_button = ttk.Button(self.options_frame, text='New Wallet',
                                            command=self.root.show_frame(WalletCreation))
        self.new_wallet_button.grid(row=2, column=0)

        self.rename_wallet = ttk.Button(self.options_frame, text='Edit Wallet')
        self.rename_wallet.grid(row=3, column=0)

        self.settings = ttk.Button(self.options_frame, text='Settings',
                                   command=lambda: Settings(self.root))
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


class WalletCreation(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.title = ttk.Label(self, text='Wallet Creation', font=(config.FONT, 14, 'bold'))
        self.title.grid(sticky='n')


def main():
    app = MainApplication()
    app.mainloop()
