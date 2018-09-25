import tkinter as tk
from tkinter import ttk

import io
import functools

from ...core import console, utils, blockchain, data


def catch_incorrect_password(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except data.IncorrectPasswordError:
            print('Error: Password Incorrect')

    return decorator


class _CMDHistory:

    def __init__(self, cmd_history: list):
        # history sorted from oldest -> newest
        self.history = cmd_history
        self._pointer = 0

    def previous(self):
        try:
            # last idx in history is latest cmd
            self._pointer += 1
            return self.history[-self._pointer]

        except IndexError:
            self._pointer -= 1
            return self.history[-self._pointer]

    def next(self):

        if self._pointer > 1:
            self._pointer -= 1
            return self.history[-self._pointer]
        else:
            self._pointer = 0
            return ''


class GUIConsoleOutput(io.IOBase):
    """ to support a constant output display, not waiting for the command
    to be fully complete, then display output to Text widget (as the output
    property on Console could only be called after the command had executed,
    barring any needlessly complex threading). Mocks stdout.
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

    def do_clearcache(self):
        """ Clears all cached API data """
        self.wallet.clear_cached_api_data()
        print('Cache cleared')

    def do_broadcast(self, hex_transaction: str):
        """ Broadcasts a signed hexadecimal transaction """
        print('Broadcasting...')
        response = blockchain.broadcast_transaction(hex_transaction)
        if response:
            print('Transaction broadcast successful')
        else:
            print('Error: Unable to broadcast transaction')

    @catch_incorrect_password
    def do_mnemonic(self, password: str):
        """ Prints wallet mnemonic phrase """
        print(self.wallet.get_mnemonic(password))

    @catch_incorrect_password
    def do_xpriv(self, password: str):
        """ Prints BIP32 master extended private key """
        print(self.wallet.get_xpriv(password))

    def do_mxpub(self):
        """ Prints BIP32 master extended public key """
        print(self.wallet.xpub)

    def do_axpub(self):
        """ Prints BIP32 account extended public key
        (should be the key used to create a watch-only wallet)
        """
        print(self.wallet.account_xpub)

    def do_wallet_metadata(self):
        """ Prints wallet metadata """
        print(self.wallet.get_metadata(name=self.wallet.name))


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

        self.scroll_bar = ttk.Scrollbar(self)
        self.scroll_bar.grid(row=0, column=1, sticky='ns')

        # bind scroll bar to Text y-view
        self.scroll_bar.config(command=self.console_text.yview)
        self.console_text.config(yscrollcommand=self.scroll_bar.set)

        self.console_entry = ttk.Entry(self)
        self.console_entry.grid(row=1, column=0, pady=(5, 0), sticky='ew')

        self._custom_out = GUIConsoleOutput(self.console_text)
        self.console = GUIConsole(root=self.root, intro=self.intro, stdout=self._custom_out)

        self.console_entry.bind('<Return>', self.execute_command)

        # use up/down arrows to scroll through command history
        self._cmd_history = _CMDHistory(self.console.command_history)
        self.console_entry.bind('<Up>', lambda x: self._set_historic_command(x, previous=True))
        self.console_entry.bind('<Down>', lambda x: self._set_historic_command(x, previous=False))

    @utils.threaded(daemon=True, name='GUI_CONSOLE_THREAD')
    def execute_command(self, event):
        cmd = event.widget.get()
        event.widget.delete(0, tk.END)

        if not cmd.strip():
            return

        # disable entry while command is executing in thread
        event.widget.insert(0, 'Executing, please wait...')
        event.widget['state'] = tk.DISABLED

        try:
            self.console.exec_cmd(cmd)

        finally:
            event.widget['state'] = tk.NORMAL
            event.widget.delete(0, tk.END)

    def _set_historic_command(self, event, previous=False):
        event.widget.delete(0, tk.END)
        if previous:
            event.widget.insert(tk.END, self._cmd_history.previous())
        else:
            event.widget.insert(tk.END, self._cmd_history.next())
