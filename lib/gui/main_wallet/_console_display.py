import tkinter as tk
from tkinter import ttk


class _ConsoleDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master, padding=5)
        self.main_wallet = main_wallet
        self.root = self.main_wallet.root

        # get the Text widget to expand into empty space
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.console = None

        self.console_text = tk.Text(self, height=10, wrap=tk.WORD, font=self.root.small_font,
                                    state=tk.DISABLED)
        self.console_text.configure(inactiveselectbackground=self.console_text.cget("selectbackground"))
        self.console_text.grid(row=0, column=0, sticky='nsew')

        self.command_entry = ttk.Entry(self)
        self.command_entry.grid(row=1, column=0, pady=(5, 0), sticky='ew')

        self.command_entry.bind('<Return>', )

    def write_console_text(self, text):
        self.console_text['state'] = tk.NORMAL
        self.console_text.insert(tk.END, text)
        self.console_text['state'] = tk.DISABLED
