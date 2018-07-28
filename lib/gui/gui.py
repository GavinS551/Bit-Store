import tkinter as tk
from tkinter import ttk

import os
import pathlib

from .. import wallet
from .wallet_select import *


class MainApplication(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.master_frame = ttk.Frame(self)

        self.master_frame.grid_columnconfigure(0, weight=1)
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.grid(row=0, column=0, sticky='nsew')

        self.frames = {}

        # adding all frames to self.frames dict, and adding them to master_grid
        for f in (WalletSelect,):
            frame = f(self)
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        # init will be done in WalletSelect class, this is a placeholder
        self.btc_wallet = wallet.Wallet

    def show_frame(self, frame):
        self.frames[frame].tkraise()
        self.update_idletasks()


def main():
    app = MainApplication()
    app.wm_title('Bit-Store')
    app.iconbitmap(os.path.join(pathlib.Path.cwd(), 'lib', 'gui',
                                'assets', 'BC_Logo_.png'))
    app.mainloop()
