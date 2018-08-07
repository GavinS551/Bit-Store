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

        tx_display = _TransactionDisplay(self)
        tx_display.insert_row('OUT', '1/1/1999', '-1.2342', '9.02')
        tx_display.grid()


class _TransactionDisplay(ttk.Frame):

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)

        self.tree_view = ttk.Treeview(self, columns=('Date', 'Amount', 'Balance'))
        self.tree_view.heading('#0', text='IN/OUT')
        self.tree_view.heading('#1', text='Date')
        self.tree_view.heading('#2', text='Amount')
        self.tree_view.heading('#3', text='Balance')

        self.tree_view.column('#0', stretch=tk.YES, width=100)
        self.tree_view.column('#1', stretch=tk.YES)
        self.tree_view.column('#2', stretch=tk.YES)
        self.tree_view.column('#3', stretch=tk.YES)

        self.tree_view.pack()


    def insert_row(self, *args):

        self.tree_view.insert('', tk.END, text=args[0], values=(args[1], args[2], args[3]))
