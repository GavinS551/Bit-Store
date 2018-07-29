import tkinter as tk
from tkinter import ttk, messagebox

import os

from .. import wallet, config, bip32


ICON = os.path.join(os.path.dirname(__file__), 'assets', 'bc_logo.ico')


class RootApplication(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.wm_title('Bit-Store')
        self.iconbitmap(ICON)

        self.master_frame = ttk.Frame(self)

        self.master_frame.grid_columnconfigure(0, weight=1)
        self.master_frame.grid_rowconfigure(0, weight=1)
        self.master_frame.pack(expand=True)

        self.frames = {}

        # adding all frames to self.frames dict, and adding them to master_grid
        for f in (WalletSelect, WalletCreation):
            frame = f(self)
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky='nsew')

        # starting frame
        self.show_frame(WalletSelect)

        # init will be done later, this is a placeholder
        self.btc_wallet = wallet.Wallet

    def show_frame(self, frame):
        f = self.frames[frame]
        f.gui_draw()
        f.tkraise()
        self.update_idletasks()

    def wallet_init(self, name, password):
        self.btc_wallet = wallet.Wallet(name=name, password=password)


class Settings(tk.Toplevel):

    def __init__(self, root):
        tk.Toplevel.__init__(self, root.master_frame)
        self.wm_title('Settings')
        self.wm_iconbitmap(ICON)


class PasswordPrompt(tk.Toplevel):

    def __init__(self, root):
        tk.Toplevel.__init__(self, root.master_frame)


class MainWallet(ttk.Frame):
    pass


class WalletSelect(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame, padding=10)

        # attributes below will be defined in gui_draw() method
        self.wallet_list = None

        # self.title_label = ttk.Label(self, text='Select Wallet:',
        #                              font=(config.FONT, 14, 'bold'))
        # self.title_label.grid(row=0, column=0, sticky='n', pady=5)
        #
        # self.wallet_list = tk.Listbox(self, width=30, height=10, font=(config.FONT, 14))
        # for i, w in enumerate(self.wallets):
        #     self.wallet_list.insert(i, w)
        #
        # self.wallet_list.grid(row=1, column=0, pady=10, padx=10, rowspan=3)
        #
        # self.scroll_bar = ttk.Scrollbar(self)
        # self.scroll_bar.grid(row=1, column=1, rowspan=3, sticky='nsw')
        # self.scroll_bar.config(command=self.wallet_list.yview)
        #
        # self.wallet_list.config(yscrollcommand=self.scroll_bar.set)
        #
        # self.options_frame = ttk.Frame(self)
        # self.options_frame.grid(row=1, column=2)
        #
        # self.options_label = ttk.Label(self.options_frame, text='Options:',
        #                                font=(config.FONT, 14, 'bold'))
        # self.options_label.grid(row=0, column=0, padx=10)
        #
        # self.select_button = ttk.Button(self.options_frame, text='Select Wallet',
        #                                 command=self.select_wallet)
        # self.select_button.grid(row=1, column=0, pady=20, sticky='ew')
        #
        # # binds a double click on listbox to trigger same method as button
        # # not sure why this only works with a lambda and one arg...
        # self.wallet_list.bind('<Double-1>', lambda x: self.select_wallet())
        #
        # self.new_wallet_button = ttk.Button(self.options_frame, text='New Wallet',
        #                                     command=lambda: self.root.show_frame(WalletCreation))
        # self.new_wallet_button.grid(row=2, column=0, sticky='ew')
        #
        # self.import_wallet_button = ttk.Button(self.options_frame, text='Import Wallet')
        # self.import_wallet_button.grid(row=3, column=0, sticky='ew')
        #
        # self.edit_wallet_button = ttk.Button(self.options_frame, text='Edit Wallet')
        # self.edit_wallet_button.grid(row=4, column=0, sticky='ew')
        #
        # self.settings_button = ttk.Button(self.options_frame, text='Settings',
        #                                   command=lambda: Settings(self.root))
        # self.settings_button.grid(row=5, column=0, pady=20, sticky='ew')

    def gui_draw(self):
        title_label = ttk.Label(self, text='Select Wallet:',
                                font=(config.FONT, 14, 'bold'))
        title_label.grid(row=0, column=0, sticky='n', pady=5)

        self.wallet_list = tk.Listbox(self, width=30, height=10, font=(config.FONT, 14))
        for i, w in enumerate(self.wallets):
            self.wallet_list.insert(i, w)

        self.wallet_list.grid(row=1, column=0, pady=10, padx=10, rowspan=3)

        scroll_bar = ttk.Scrollbar(self)
        scroll_bar.grid(row=1, column=1, rowspan=3, sticky='nsw')
        scroll_bar.config(command=self.wallet_list.yview)

        self.wallet_list.config(yscrollcommand=scroll_bar.set)

        options_frame = ttk.Frame(self)
        options_frame.grid(row=1, column=2)

        options_label = ttk.Label(options_frame, text='Options:',
                                  font=(config.FONT, 14, 'bold'))
        options_label.grid(row=0, column=0, padx=10)

        select_button = ttk.Button(options_frame, text='Select Wallet',
                                   command=self.select_wallet)
        select_button.grid(row=1, column=0, pady=20, sticky='ew')

        # binds a double click on listbox to trigger same method as button
        # not sure why this only works with a lambda and one arg...
        self.wallet_list.bind('<Double-1>', lambda x: self.select_wallet())

        new_wallet_button = ttk.Button(options_frame, text='New Wallet',
                                       command=lambda: self.root.show_frame(WalletCreation))
        new_wallet_button.grid(row=2, column=0, sticky='ew')

        import_wallet_button = ttk.Button(options_frame, text='Import Wallet')
        import_wallet_button.grid(row=3, column=0, sticky='ew')

        edit_wallet_button = ttk.Button(options_frame, text='Edit Wallet')
        edit_wallet_button.grid(row=4, column=0, sticky='ew')

        settings_button = ttk.Button(options_frame, text='Settings',
                                     command=lambda: Settings(self.root))
        settings_button.grid(row=5, column=0, pady=20, sticky='ew')

    @property
    def wallets(self):
        # list of all directories in program's DATA_DIR (i.e all wallets)
        return [w for w in os.listdir(config.DATA_DIR)
                if os.path.isdir(os.path.join(config.DATA_DIR, w))]

    def select_wallet(self):
        try:
            selected_wallet = self.wallets[self.wallet_list.curselection()[0]]
            print(selected_wallet)

        except IndexError:
            messagebox.showerror('Error', 'No wallet selected!')


class WalletCreation(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame, padding=10)

        self.small_font = (config.FONT, 10)
        self.tiny_font = (config.FONT, 8)

        # attributes below will be defined in gui_draw()
        self.password_entry = None
        self.confirm_pass_entry = None
        self.path_entry = None
        self.segwit_check = None
        self.name_entry = None
        self.mnemonic_passphrase_entry = None

        # self.title = ttk.Label(self, text='Wallet Creation:', font=(config.FONT, 14, 'bold'))
        # self.title.grid(row=0, column=0, sticky='n', pady=10)
        #
        # self.required_label = ttk.Label(self, text='* Required entries', font=self.tiny_font)
        # self.required_label.grid(row=0, column=1)
        #
        # self.name_label = ttk.Label(self, text='Enter Name:*', font=self.small_font)
        # self.name_label.grid(row=1, column=0, sticky='w')
        #
        # self.name_entry = ttk.Entry(self)
        # self.name_entry.grid(row=1, column=1, pady=5)
        #
        # self.password_label = ttk.Label(self, text='Enter Password:*', font=self.small_font)
        # self.password_label.grid(row=2, column=0, sticky='w')
        #
        # self.password_entry = ttk.Entry(self, show='*')
        # self.password_entry.grid(row=2, column=1, pady=5)
        #
        # self.confirm_pass_label = ttk.Label(self, text='Confirm Password:*', font=self.small_font)
        # self.confirm_pass_label.grid(row=3, column=0, sticky='w')
        #
        # self.confirm_pass_entry = ttk.Entry(self, show='*')
        # self.confirm_pass_entry.grid(row=3, column=1, pady=5)
        #
        # self.path_label = ttk.Label(self, text='Custom Derivation Path:', font=self.small_font)
        # self.path_label.grid(row=4, column=0, sticky='w')
        #
        # self.path_entry = ttk.Entry(self)
        # self.path_entry.insert(tk.END, config.BIP32_PATHS['bip49path'])
        # self.path_entry.grid(row=4, column=1, pady=5)
        #
        # self.optional_label0 = ttk.Label(self, text='(optional)', font=self.tiny_font)
        # self.optional_label0.grid(row=4, column=2, padx=5)
        #
        # self.segwit_label = ttk.Label(self, text='Segwit Enabled:', font=self.small_font)
        # self.segwit_label.grid(row=5, column=0, sticky='w')
        #
        # self.segwit_check = tk.IntVar(value=1)
        # self.segwit_enabled_check = ttk.Checkbutton(self, variable=self.segwit_check)
        # self.segwit_enabled_check.grid(row=5, column=1, pady=5)
        #
        # self.recommend_label = ttk.Label(self, text='(recommended)', font=self.tiny_font)
        # self.recommend_label.grid(row=5, column=2)
        #
        # self.mnemonic_passphrase_label = ttk.Label(self, text='Mnemonic Passphrase:', font=self.small_font)
        # self.mnemonic_passphrase_label.grid(row=6, column=0, sticky='w')
        #
        # self.mnemonic_passphrase_entry = ttk.Entry(self)
        # self.mnemonic_passphrase_entry.grid(row=6, column=1, pady=5)
        #
        # self.optional_label1 = ttk.Label(self, text='(optional)', font=self.tiny_font)
        # self.optional_label1.grid(row=6, column=2, padx=5)
        #
        # self.back_button = ttk.Button(self, text='Back',
        #                               command=lambda: self.root.show_frame(WalletSelect))
        # self.back_button.grid(row=7, column=0, sticky='sw', pady=20)
        #
        # self.create_button = ttk.Button(self, text='Create Wallet', command=self.create_wallet)
        # self.create_button.grid(row=7, column=1, sticky='se', pady=20)

    def gui_draw(self):
        title = ttk.Label(self, text='Wallet Creation:', font=(config.FONT, 14, 'bold'))
        title.grid(row=0, column=0, sticky='n', pady=10)

        required_label = ttk.Label(self, text='* Required entries', font=self.tiny_font)
        required_label.grid(row=0, column=1)

        name_label = ttk.Label(self, text='Enter Name:*', font=self.small_font)
        name_label.grid(row=1, column=0, sticky='w')

        name_entry = ttk.Entry(self)
        name_entry.grid(row=1, column=1, pady=5)

        password_label = ttk.Label(self, text='Enter Password:*', font=self.small_font)
        password_label.grid(row=2, column=0, sticky='w')

        self.password_entry = ttk.Entry(self, show='*')
        self.password_entry.grid(row=2, column=1, pady=5)

        confirm_pass_label = ttk.Label(self, text='Confirm Password:*', font=self.small_font)
        confirm_pass_label.grid(row=3, column=0, sticky='w')

        self.confirm_pass_entry = ttk.Entry(self, show='*')
        self.confirm_pass_entry.grid(row=3, column=1, pady=5)

        path_label = ttk.Label(self, text='Custom Derivation Path:', font=self.small_font)
        path_label.grid(row=4, column=0, sticky='w')

        self.path_entry = ttk.Entry(self)
        self.path_entry.insert(tk.END, config.BIP32_PATHS['bip49path'])
        self.path_entry.grid(row=4, column=1, pady=5)

        optional_label0 = ttk.Label(self, text='(optional)', font=self.tiny_font)
        optional_label0.grid(row=4, column=2, padx=5)

        segwit_label = ttk.Label(self, text='Segwit Enabled:', font=self.small_font)
        segwit_label.grid(row=5, column=0, sticky='w')

        self.segwit_check = tk.IntVar(value=1)
        segwit_enabled_check = ttk.Checkbutton(self, variable=self.segwit_check)
        segwit_enabled_check.grid(row=5, column=1, pady=5)

        recommend_label = ttk.Label(self, text='(recommended)', font=self.tiny_font)
        recommend_label.grid(row=5, column=2)

        mnemonic_passphrase_label = ttk.Label(self, text='Mnemonic Passphrase:', font=self.small_font)
        mnemonic_passphrase_label.grid(row=6, column=0, sticky='w')

        self.mnemonic_passphrase_entry = ttk.Entry(self)
        self.mnemonic_passphrase_entry.grid(row=6, column=1, pady=5)

        optional_label1 = ttk.Label(self, text='(optional)', font=self.tiny_font)
        optional_label1.grid(row=6, column=2, padx=5)

        back_button = ttk.Button(self, text='Back',
                                 command=lambda: self.root.show_frame(WalletSelect))
        back_button.grid(row=7, column=0, sticky='sw', pady=20)

        create_button = ttk.Button(self, text='Create Wallet', command=self.create_wallet)
        create_button.grid(row=7, column=1, sticky='se', pady=20)

    def _verify_password(self):
        return self.password_entry.get() == self.confirm_pass_entry.get()

    def create_wallet(self):
        try:
            name = self.name_entry.get()
            password = self.password_entry.get()

            if self.path_entry.get() == '':
                # setting default path
                path = config.BIP32_PATHS['bip49path']
            else:
                path = self.path_entry.get()

            is_segwit = True if self.segwit_check.get() == 1 else False

            # error checking
            if not name:
                raise ValueError('No name entered!')

            if not password:
                raise ValueError('No password entered!')

            if not self._verify_password():
                self.password_entry.delete(0, 'end')
                self.confirm_pass_entry.delete(0, 'end')
                raise ValueError('Passwords don\'t match!')

            if not bip32.Bip32.check_path(path):
                raise ValueError(f'Invalid path entered: ({path})')

        except Exception as ex:
            tk.messagebox.showerror('Error', f'{ex.__str__()}')


def main():
    app = RootApplication()
    app.mainloop()
