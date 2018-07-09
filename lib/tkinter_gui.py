import os

import tkinter as tk
from tkinter import ttk

from src import config

FONT = ('Helvetica', 16, 'bold')


class WalletSelect(ttk.Frame):

    def __init__(self, parent, controller):

        ttk.Frame.__init__(self, parent)

        self.controller = controller
        self.controller.minsize(width=500, height=250)

        ttk.Label(text='Wallet Selection', font=FONT).grid(row=0, column=0, sticky='N')

        select_var = tk.StringVar(self)
        select_menu = ttk.OptionMenu(self, select_var, *self._wallets)
        select_menu.grid(row=3, column=0, sticky='SW')

        ttk.Button(self, text='Select Wallet').grid(row=3, column=0, sticky='SE')

    @property
    def _wallets(self):
        # finds all dirs in config.DATA_DIR, all of which should be wallets
        return [w for w in os.listdir(config.DATA_DIR)
                if os.path.isdir(os.path.join(config.DATA_DIR, w))]

class MainApplication(tk.Tk):

    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)
        container = ttk.Frame(self)

        container.grid()
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        frame = WalletSelect(container, self)

        self.frames[WalletSelect] = frame

        frame.grid(row=10, column=10, sticky='nsew')

        self.show_frame(WalletSelect)

    def show_frame(self, controller):
        frame = self.frames[controller]
        frame.tkraise()
        # tk.Tk.update(self)


if __name__ == '__main__':
    app = MainApplication()
    app.mainloop()
