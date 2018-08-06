import tkinter as tk
from tkinter import ttk


class MainWallet(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

    def gui_draw(self):
        title_label = ttk.Label(self, text=self.root.btc_wallet.name,
                                font=self.root.bold_title_font)
        title_label.grid(row=0, column=0)
