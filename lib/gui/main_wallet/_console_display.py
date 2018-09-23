import tkinter as tk
from tkinter import ttk

import io

from ...core import console, utils


class GUIConsoleOutput(io.IOBase):
    """ to support a constant output display, not waiting for the command
     to be fully complete, then display output to Text widget
    """
    prompt_text = '>> '

    def __init__(self, tk_text, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.tk_text = tk_text
        self.tk_text['state'] = tk.DISABLED

    def write(self, text):
        self.tk_text['state'] = tk.NORMAL

        new_text = text.replace('\n', f'\n{self.prompt_text}')

        self.tk_text.insert(tk.END, new_text)
        self.tk_text.see('end')

        self.tk_text['state'] = tk.DISABLED

    def getvalue(self):
        self.tk_text['state'] = tk.NORMAL
        val = self.tk_text.get(1.0, 'end-1c')
        self.tk_text['state'] = tk.DISABLED

        return val

    def seek(self, *args, **kwargs):
        pass

    def read(self):
        pass

    def truncate(self, *args, **kwargs):
        self.tk_text['state'] = tk.NORMAL
        self.tk_text.delete(1.0, tk.END)
        self.tk_text.insert(tk.END, self.prompt_text)
        self.tk_text['state'] = tk.DISABLED


class GUIConsole(console.Console):

    def __init__(self, root, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root
        self.wallet = self.root.btc_wallet

    def do_clear(self):
        self.clear_output()

    def do_addresses(self):
        """ Prints all wallet addresses. """
        print(self.wallet.all_addresses)


class ConsoleDisplay(ttk.Frame):

    intro = 'Bit-Store Console. Please type ? or "help" for a list of possible commands.\n'
    console_font = ('consolas', 10)

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master, padding=5)
        self.main_wallet = main_wallet
        self.root = self.main_wallet.root

        # get the Text widget to expand into empty space
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.console_text = tk.Text(self, height=10, wrap=tk.WORD, font=self.console_font,
                                    state=tk.DISABLED)
        self.console_text.configure(inactiveselectbackground=self.console_text.cget("selectbackground"))
        self.console_text.grid(row=0, column=0, sticky='nsew')

        self.console_entry = ttk.Entry(self)
        self.console_entry.grid(row=1, column=0, pady=(5, 0), sticky='ew')

        self._custom_out = GUIConsoleOutput(self.console_text)
        self.console = GUIConsole(root=self.root, intro=self.intro, stdout=self._custom_out)

        self.console_entry.bind('<Return>', self.execute_command)

    @utils.threaded(daemon=True, name='GUI_CONSOLE_THREAD')
    def execute_command(self, event):
        cmd = event.widget.get()
        event.widget.delete(0, tk.END)

        # disable entry while command is executing in thread
        event.widget.insert(0, 'Executing, please wait...')
        event.widget['state'] = tk.DISABLED

        try:
            self.console.exec_cmd(cmd)

        finally:
            event.widget['state'] = tk.NORMAL
            event.widget.delete(0, tk.END)
