import tkinter as tk
from tkinter import ttk, messagebox

from .wallet_creation import WalletCreation
from ..core import hd


class WalletImport(WalletCreation):

    def gui_draw(self):
        super().gui_draw()
        self.title.config(text='Wallet Import:')

        self.create_button.config(text='Next',
                                  command=self.on_next)

        self.mnemonic_passphrase_label.grid_remove()
        self.mnemonic_passphrase_entry.grid_remove()

    def import_type_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.grab_set()
        dialog.iconbitmap(self.root.ICON)

        selected_type = tk.StringVar()

        main_frame = ttk.Frame(dialog, padding=10)

        title = ttk.Label(main_frame, text='Select Import Type:', font=self.root.small_font + ('bold',))
        title.grid(row=0, column=0, pady=10, padx=20, sticky='w')

        mnemonic_radio = ttk.Radiobutton(main_frame, text='Mnemonic Import',
                                         variable=selected_type, value='mnemonic')
        mnemonic_radio.grid(row=1, column=0, pady=5, padx=20, sticky='w')

        xkey_radio = ttk.Radiobutton(main_frame, text='BIP32 Extended Key Import',
                                     variable=selected_type, value='xkey')
        xkey_radio.grid(row=2, column=0, pady=5, padx=20, sticky='w')

        button_frame = ttk.Frame(main_frame)

        ok_button = ttk.Button(button_frame, text='OK', command=dialog.destroy)
        ok_button.grid(row=0, column=0, pady=10, padx=10, sticky='w')

        cancel_button = ttk.Button(button_frame, text='Cancel', command=dialog.destroy)
        cancel_button.grid(row=0, column=1, pady=10, padx=10, sticky='e')

        button_frame.grid(row=3, column=0)

        main_frame.grid(row=0, column=0, sticky='nsew')

        # waits for the window to be destroyed by the select button
        # so selected type wont be returned instantly
        self.root.wait_window(dialog)

        return selected_type.get()

    def on_next(self):
        if not all([entry.get() for entry in (self.password_entry,
                                              self.confirm_pass_entry, self.name_entry)]):
            tk.messagebox.showerror('Error', 'Please fill out all required entries before continuing')

        else:
            import_type = self.import_type_dialog()

            if not import_type:
                return

            self.root.show_frame('WalletImportPage2', wallet_import=self, import_type=import_type)


class WalletImportPage2(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        # set from root.show_frame method
        self.wallet_import = None
        self.import_type = None

        # set in gui_draw
        self.entry_label = None
        self.entry = None
        self.passphrase_entry_label = None
        self.passphrase_entry = None

    def gui_draw(self):

        if self.import_type not in ('xkey', 'mnemonic'):
            raise ValueError('Import type must be either "xkey" or "mnemonic"')

        entry_text = 'Enter Mnemonic:*' if self.import_type == 'mnemonic' else 'Enter Extended Key:*'

        title = ttk.Label(self, text='Wallet Import:', font=self.root.bold_title_font)
        title.grid(row=0, column=0, pady=10, sticky='w')

        required_label = ttk.Label(self, text=' * Required entries', font=self.root.tiny_font)
        required_label.grid(row=0, column=1, sticky='w')

        self.entry_label = ttk.Label(self, text=entry_text, font=self.root.small_font)
        self.entry_label.grid(row=1, column=0, padx=(0, 20), sticky='w')

        self.entry = tk.Text(self, width=40, height=5, font=self.root.small_font, wrap=tk.WORD)
        self.entry.grid(row=1, column=1, pady=20)

        if self.import_type == 'mnemonic':
            self.passphrase_entry_label = ttk.Label(self, text='Mnemonic Passphrase:', font=self.root.small_font)
            self.passphrase_entry_label.grid(row=2, column=0, padx=(0, 20), sticky='w')

            self.passphrase_entry = ttk.Entry(self)
            self.passphrase_entry.grid(row=2, column=1, pady=20, sticky='ew')

        back_button = ttk.Button(self, text='Back', command=self.on_back)
        back_button.grid(row=3, column=0, padx=10, pady=20, sticky='e')

        create_button = ttk.Button(self, text='Create', command=self.on_create)
        create_button.grid(row=3, column=1, padx=10, pady=20, sticky='w')

    def on_back(self):
        # remove the optional widgets, because if the user goes back
        # and doesnt select the mnemonic import, these widgets will still be
        # in the frame and will overlap with other labels/entries
        self.passphrase_entry_label.grid_remove()
        self.passphrase_entry.grid_remove()

        self.root.show_frame('WalletImport')

    def on_create(self):
        if self.import_type == 'mnemonic':
            mnemonic = self.entry.get(1.0, 'end-1c')
            passphrase = self.passphrase_entry.get()

            if not hd.HDWallet.check_mnemonic(mnemonic):
                tk.messagebox.showerror('Error', 'Invalid Mnemonic Entered')
                return

            self.wallet_import.create_wallet(mnemonic=mnemonic, passphrase=passphrase)

        else:
            xkey = self.entry.get(1.0, 'end-1c')

            if not hd.HDWallet.check_xkey(xkey, allow_testnet=False):
                tk.messagebox.showerror('Error', 'Invalid extended key entered')

            if xkey[1:4] == 'pub':
                tk.messagebox.showerror('Error', 'Public key entered: watch-only wallets not currently supported')

            self.wallet_import.create_wallet(xkey=xkey)
