# Copyright (C) 2018  Gavin Shaughnessy
#
# Bit-Store is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import tkinter as tk
from tkinter import ttk, messagebox

from .wallet_creation import WalletCreation
from ..core import hd


class WalletImport(WalletCreation):

    def gui_draw(self):
        super().gui_draw()
        self.title.config(text='Wallet Import:')

        self.recommend_label.grid_remove()

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
        try:
            self._validate_entries()

            import_type = self.import_type_dialog()

            if not import_type:
                return

            self.root.show_frame('WalletImportPage2', wallet_import=self, import_type=import_type)

        except ValueError as ex:
            messagebox.showerror('Error', f'{ex.__str__()}')


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
        self.entry.grid(row=1, column=1, pady=10)

        if self.import_type == 'mnemonic':
            self.passphrase_entry_label = ttk.Label(self, text='Mnemonic Passphrase:', font=self.root.small_font)
            self.passphrase_entry_label.grid(row=2, column=0, padx=(0, 20), sticky='w')

            self.passphrase_entry = ttk.Entry(self)
            self.passphrase_entry.grid(row=2, column=1, pady=10, sticky='ew')

        back_button = ttk.Button(self, text='Back', command=self.on_back)
        back_button.grid(row=3, column=0, padx=10, pady=20, sticky='e')

        col_2_button_frame = ttk.Frame(self)

        create_button = ttk.Button(col_2_button_frame, text='Create', command=self.on_create)
        create_button.grid(row=0, column=0, padx=10, pady=10, sticky='w')

        advanced_button = ttk.Button(col_2_button_frame, text='Advanced', command=self.wallet_import.advanced_window)
        advanced_button.grid(row=0, column=1, padx=(110, 10), pady=10, sticky='e')

        col_2_button_frame.grid(row=3, column=1, sticky='ew')

    def on_back(self):
        # remove the optional widgets, or labels that change due to different
        # attributes, because if the user goes back and doesn't select the
        # mnemonic import, these widgets will still be
        # in the frame and will overlap with other labels/entries that change
        if self.passphrase_entry_label is not None:
            self.passphrase_entry_label.grid_remove()

        if self.passphrase_entry is not None:
            self.passphrase_entry.grid_remove()

        self.entry_label.grid_remove()

        self.root.show_frame('WalletImport')

    def on_create(self):
        # getting advanced settings

        if self.import_type == 'mnemonic':
            mnemonic = self.entry.get(1.0, 'end-1c').strip()
            passphrase = self.passphrase_entry.get().strip()

            if not hd.HDWallet.check_mnemonic(mnemonic.lower()):
                tk.messagebox.showerror('Error', 'Invalid Mnemonic Entered')
                return

            self.wallet_import.create_wallet(mnemonic=mnemonic, passphrase=passphrase,
                                             force_no_mnemonic_display=True)

        else:
            xkey = self.entry.get(1.0, 'end-1c').strip()

            if not hd.HDWallet.check_xkey(xkey, allow_testnet=False):
                tk.messagebox.showerror('Error', 'Invalid extended key entered')
                return

            if xkey[1:4] == 'pub':
                tk.messagebox.showinfo('Watch-Only', 'A public extended key was entered. '
                                                     'This will create a "watch-only" wallet '
                                                     'that you will not be able to spend bitcoin '
                                                     'with, but you will be able to create and '
                                                     'export unsigned transactions, and monitor '
                                                     'wallet activity.')

                # watch only wallets will have a path of m as they should be the xpub of the account
                # to be monitored
                self.wallet_import.path_entry.delete(0, tk.END)
                self.wallet_import.path_entry.insert(tk.END, 'm')

            self.wallet_import.create_wallet(xkey=xkey)
