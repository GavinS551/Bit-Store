import tkinter as tk
from tkinter import ttk

import os

from lib import config, wallet, bip32  # change to .. after testing


class MainApplication(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        container = ttk.Frame(self)

        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        container.grid(row=0, column=0)#, sticky='nsew')

        self.frames = {}

        # adding all frames to self.frames dict, and adding them to grid
        for f in (WalletSelect,):
            frame = f(container, self)
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        # init will be done in WalletSelect class, this is a placeholder
        self.btc_wallet = wallet.Wallet

    def show_frame(self, container):
        self.frames[container].tkraise()
        self.update_idletasks()


class WalletSelect(ttk.Frame):

    def __init__(self, parent, root):
        ttk.Frame.__init__(self, parent)
        #root.minsize(800, 500)

        self.wallet_list = tk.Listbox(self)
        for i, w in enumerate(self.wallets):
            self.wallet_list.insert(i, w)

        self.wallet_list.grid(sticky='w')

    @property
    def wallets(self):
        # list of all directories in program's DATA_DIR (i.e all wallets)
        return [w for w in os.listdir(config.DATA_DIR) if os.path.isdir(os.path.join(config.DATA_DIR, w))]


if __name__ == '__main__':

    app = MainApplication()
    app.mainloop()
