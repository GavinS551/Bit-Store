import tkinter as tk
from tkinter import ttk

from .wallet_creation import WalletCreation


class WalletImport(WalletCreation):

    def gui_draw(self):
        super().gui_draw()
        self.title.config(text='Wallet Import:')

        


