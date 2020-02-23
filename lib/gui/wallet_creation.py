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

from typing import NamedTuple, Union
import string
import queue

from ..core import config, wallet, hd, utils


MAX_NAME_LENGTH = 25


class WalletCreation(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.grid_columnconfigure(2, {'minsize': 100})

        # attributes below will be defined in gui_draw()
        self.password_entry = None
        self.confirm_pass_entry = None
        self.path_entry = None
        self.segwit_check = None
        self.name_entry = None
        self.mnemonic_passphrase_entry = None
        self.recommend_label = None

        # attributes for subclass support
        self.title = None
        self.mnemonic_passphrase_label = None
        self.back_button = None
        self.create_button = None
        self.advanced_button = None

        # set from self.advanced_window
        # the keys MUST be valid HDWallet obj params
        self.adv_settings = {
            'gap_limit': 20,
            'force_public': False,
            'multi_processing': True,
        }
        self._adv_warning_shown = False

    def gui_draw(self):
        self.title = ttk.Label(self, text='Wallet Creation:', font=self.root.bold_title_font)
        self.title.grid(row=0, column=0, sticky='w', pady=10)

        required_label = ttk.Label(self, text=' * Required entries', font=self.root.tiny_font)
        required_label.grid(row=0, column=1)

        name_label = ttk.Label(self, text='Enter Name:*', font=self.root.small_font)
        name_label.grid(row=1, column=0, sticky='w')

        self.name_entry = ttk.Entry(self)
        self.name_entry.grid(row=1, column=1, pady=5, columnspan=2)

        password_label = ttk.Label(self, text='Enter Password:*', font=self.root.small_font)
        password_label.grid(row=2, column=0, sticky='w')

        self.password_entry = ttk.Entry(self, show='●')
        self.password_entry.grid(row=2, column=1, pady=5, columnspan=2)

        confirm_pass_label = ttk.Label(self, text='Confirm Password:*', font=self.root.small_font)
        confirm_pass_label.grid(row=3, column=0, sticky='w')

        self.confirm_pass_entry = ttk.Entry(self, show='●')
        self.confirm_pass_entry.grid(row=3, column=1, pady=5, columnspan=2)

        path_label = ttk.Label(self, text='Custom Path:', font=self.root.small_font)
        path_label.grid(row=4, column=0, sticky='w')

        self.path_entry = ttk.Entry(self)
        self.path_entry.grid(row=4, column=1, pady=5, columnspan=2)

        path_default = ttk.Label(self, text='(Default: 49\'/0\'/0\')', font=self.root.tiny_font)
        path_default.grid(row=4, column=3, padx=5, sticky='w')

        segwit_label = ttk.Label(self, text='Segwit Enabled:', font=self.root.small_font)
        segwit_label.grid(row=5, column=0, sticky='w')

        self.segwit_check = tk.IntVar(value=1)
        segwit_enabled_check = ttk.Checkbutton(self, variable=self.segwit_check)
        segwit_enabled_check.grid(row=5, column=1, pady=5)

        self.recommend_label = ttk.Label(self, text='(Recommended)', font=self.root.tiny_font)
        self.recommend_label.grid(row=5, column=3, padx=5, sticky='w')

        self.mnemonic_passphrase_label = ttk.Label(self, text='Mnemonic Passphrase:', font=self.root.small_font)
        self.mnemonic_passphrase_label.grid(row=6, column=0, sticky='w')

        self.mnemonic_passphrase_entry = ttk.Entry(self)
        self.mnemonic_passphrase_entry.grid(row=6, column=1, pady=5, columnspan=2)

        self.back_button = ttk.Button(self, text='Back',
                                      command=lambda: self.root.show_frame('WalletSelect'))
        self.back_button.grid(row=7, column=0, sticky='e', padx=10, pady=20)

        self.create_button = ttk.Button(self, text='Create', command=self.create_wallet)
        self.create_button.grid(row=7, column=1, sticky='w', padx=10, pady=20)

        self.advanced_button = ttk.Button(self, text='Advanced', command=self.advanced_window)
        self.advanced_button.grid(row=7, column=3, sticky='w', padx=10, pady=20)

    def _verify_password(self):
        return self.password_entry.get() == self.confirm_pass_entry.get()

    def _validate_entries(self):
        """ invalid entries raise ValueError """
        name = self.name_entry.get().strip()
        password = self.password_entry.get()

        if self.path_entry.get() == '':
            # setting default path
            path = config.BIP32_PATHS['bip49path']
        else:
            path = self.path_entry.get()

        if not name:
            raise ValueError('No name entered')

        if len(name) > MAX_NAME_LENGTH:
            raise ValueError(f'Name is too long (max={MAX_NAME_LENGTH})')

        if not all(c in string.ascii_letters + string.digits + ' ' for c in name):
            raise ValueError('Name must only contain standard alphanumeric characters or spaces')

        for w in self.root.frames['WalletSelect'].wallets:
            if w.lower() == name.lower():
                raise ValueError('Wallet with same name already exists!')

        if not password:
            raise ValueError('No password entered')

        if not self._verify_password():
            self.password_entry.delete(0, 'end')
            self.confirm_pass_entry.delete(0, 'end')
            raise ValueError('Passwords don\'t match')

        if not hd.HDWallet.check_path(path):
            raise ValueError(f'Invalid path entered: ({path})')

    def advanced_window(self):
        gap_limit_var = tk.StringVar(value=str(self.adv_settings['gap_limit']))
        force_watch_only_var = tk.BooleanVar(value=self.adv_settings['force_public'])
        multi_processing_var = tk.BooleanVar(value=self.adv_settings['multi_processing'])

        def gap_limit_entry_validate(entry):
            return entry.isdigit() or not entry

        def on_save():

            prev_settings = self.adv_settings.copy()

            self.adv_settings['gap_limit'] = int(gap_limit_var.get())
            self.adv_settings['force_public'] = force_watch_only_var.get()
            self.adv_settings['multi_processing'] = multi_processing_var.get()

            toplevel.destroy()

            if self.adv_settings != prev_settings:
                messagebox.showinfo('Saved', 'Advanced settings saved')

        if not self._adv_warning_shown:
            # warning to user that some options can break things
            messagebox.showwarning('Advanced Options - Warning', 'Only change these settings '
                                                                 'if you understand what you are doing. '
                                                                 'Some advanced settings may not be stable '
                                                                 'and could lead to loss of Bitcoin if you '
                                                                 'use the resulting wallet.')
            self._adv_warning_shown = True

        toplevel = self.root.get_toplevel(self)
        toplevel.grab_set()
        frame = ttk.Frame(toplevel, padding=10)

        gap_limit_label = ttk.Label(frame, text='Gap limit:', font=self.root.small_font + ('bold',))
        gap_limit_label.grid(row=0, column=0, padx=10, pady=5, sticky='w')

        gap_limit_validate = self.root.register(gap_limit_entry_validate)
        gap_limit_entry = ttk.Entry(frame, textvariable=gap_limit_var, width=10, validate='key',
                                    validatecommand=(gap_limit_validate, '%P'))
        gap_limit_entry.grid(row=0, column=1, padx=10, sticky='e')

        force_watch_only_label = ttk.Label(frame, text='Force watch-only:', font=self.root.small_font + ('bold',))
        force_watch_only_label.grid(row=1, column=0, padx=10, pady=5, sticky='w')

        force_watch_only_check = ttk.Checkbutton(frame, variable=force_watch_only_var, offvalue=False,
                                                 onvalue=True)
        force_watch_only_check.grid(row=1, column=1, padx=10, sticky='e')

        multi_processing_label = ttk.Label(frame, text='Multiprocessing:', font=self.root.small_font + ('bold',))
        multi_processing_label.grid(row=2, column=0, padx=10, pady=5, sticky='w')

        multi_processing_check = ttk.Checkbutton(frame, variable=multi_processing_var, offvalue=False,
                                                 onvalue=True)
        multi_processing_check.grid(row=2, column=1, padx=10, sticky='e')

        frame.grid(row=0, column=0, sticky='nsew')

        save_button = ttk.Button(toplevel, text='Save', command=on_save)
        save_button.grid(row=1, column=0, padx=10, pady=(0, 10))

    # custom mnemonic and xkey params are meant for subclassing this class when
    # implementing wallet import feature
    def create_wallet(self, mnemonic=None, xkey=None, passphrase=None,
                      force_no_mnemonic_display=False):
        # getting any advanced settings that were set
        hd_wallet_adv_data = self.adv_settings

        if mnemonic is None and xkey is None:
            mnemonic = hd.HDWallet.gen_mnemonic()

        if passphrase is None:
            passphrase = self.mnemonic_passphrase_entry.get()

        try:
            name = self.name_entry.get().strip()
            password = self.password_entry.get()

            if self.path_entry.get() == '':
                # setting default path
                path = config.BIP32_PATHS['bip49path']
            else:
                path = self.path_entry.get()

            is_segwit = True if self.segwit_check.get() == 1 else False

            # error checking, invalid entries raise ValueError
            self._validate_entries()

            if None not in [mnemonic, xkey]:
                raise ValueError('Either "mnemonic" or "xkey" arguments must be None')
            elif all(x is None for x in [mnemonic, xkey]):
                raise ValueError('Either "mnemonic" or "xkey" arguments must have a value')

            class WalletCreationData(NamedTuple):

                name: str
                password: str
                passphrase: str
                is_segwit: bool
                path: str
                mnemonic: Union[str, None]
                xkey: Union[str, None]

            wd = WalletCreationData(name, password, passphrase,
                                    is_segwit, path, mnemonic, xkey)

            # thread is already started, see utils.threaded decorator
            self._build_wallet_instance(wd, hd_adv_data=hd_wallet_adv_data,
                                        force_no_mnemonic_display=force_no_mnemonic_display)

        except ValueError as ex:
            messagebox.showerror('Error', str(ex))

            # if loading screen had started, go back
            self.root.show_frame(self.__class__.__name__)

    @utils.threaded(name='GUI_MAKE_WALLET_THREAD')
    def _build_wallet_instance(self, wallet_data, hd_adv_data=None,
                               force_no_mnemonic_display=False):
        message_queue = queue.Queue()
        self.root.show_frame('WalletCreationLoading', loading_messages_queue=message_queue)

        if hd_adv_data is None:
            hd_adv_data = {}

        try:
            if wallet_data.xkey is None:
                message_queue.put('Deriving addresses from mnemonic...')
                hd_ = hd.HDWallet.from_mnemonic(wallet_data.mnemonic,
                                                wallet_data.path,
                                                wallet_data.passphrase,
                                                wallet_data.is_segwit,
                                                **hd_adv_data)
                watch_only_wallet = not hd_.is_private
                bypass_mnemonic_display = watch_only_wallet

            else:
                message_queue.put('Deriving addresses from xkey...')
                hd_ = hd.HDWallet(wallet_data.xkey,
                                  wallet_data.path,
                                  wallet_data.is_segwit,
                                  **hd_adv_data)

                watch_only_wallet = not hd_.is_private
                bypass_mnemonic_display = True

            message_queue.put('Addresses generated...')

            message_queue.put('Creating new wallet...')
            if watch_only_wallet:
                w = wallet.WatchOnlyWallet.new_wallet(wallet_data.name, wallet_data.password, hd_)
            else:
                w = wallet.Wallet.new_wallet(wallet_data.name, wallet_data.password, hd_)
            message_queue.put('Wallet created...')

            self.root.btc_wallet = w

            if bypass_mnemonic_display or force_no_mnemonic_display:
                if watch_only_wallet:
                    self.root.show_frame('WatchOnlyMainWallet')
                else:
                    self.root.show_frame('MainWallet')
            else:
                self.root.show_frame('WalletCreationShowMnemonic', mnemonic=wallet_data.mnemonic)

        except Exception:
            # if an exception was raised, leave loading frame
            self.root.show_frame(self.__class__.__name__)
            self.root.show_traceback()


class WalletCreationLoading(ttk.Frame):

    def __init__(self, root):
        self.root = root
        ttk.Frame.__init__(self, self.root.master_frame)

        self.grid_rowconfigure(0, {'minsize': 50})
        self.grid_columnconfigure(0, {'minsize': 35})

        # threading.Queue that will be updated with loading messages outside class
        # set from show_frame method
        self.loading_messages_queue = None

        self.cur_message = tk.StringVar()

    def gui_draw(self):
        self._set_latest_message()

        title = ttk.Label(self, text='Creating Wallet, Please Wait...',
                          font=self.root.bold_title_font)
        title.grid(row=1, column=1, sticky='n')

        loading_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=400, mode='indeterminate')
        loading_bar.grid(row=2, column=1, pady=40, padx=20)
        loading_bar.start()

        message = ttk.Label(self, textvariable=self.cur_message, font=self.root.small_font)
        message.grid(row=3, column=1)

    def _set_latest_message(self):
        while True:
            try:
                message = self.loading_messages_queue.get_nowait()
                self.cur_message.set(message)

            except queue.Empty:
                break

        self.root.after(100, self._set_latest_message)


class WalletCreationShowMnemonic(ttk.Frame):

    def __init__(self, root):
        self.root = root
        self.mnemonic = None  # mnemonic will be set from show_frame
        ttk.Frame.__init__(self, self.root.master_frame)

    def gui_draw(self):
        title_label = ttk.Label(self, text='Wallet Mnemonic Seed:', font=self.root.bold_title_font)
        title_label.grid(row=0, column=0, sticky='n', pady=20)

        info_label = ttk.Label(self, text='Please write down the mnemonic phrase below '
                                          'and keep it in a safe place as it contains all information '
                                          'needed to spend your Bitcoin. This is how you can recover '
                                          'your wallet in the future.',
                               font=self.root.small_font,
                               justify=tk.CENTER, wrap=520)
        info_label.grid(row=1, column=0)

        mnemonic_label = ttk.Label(self, text=self.mnemonic, font=('Courier New', 14, 'bold'),
                                   wrap=350, justify=tk.CENTER)
        mnemonic_label.grid(row=2, column=0, pady=30)

        continue_button = ttk.Button(self, text='Continue',
                                     command=lambda: self.root.show_frame('WalletCreationVerifyMnemonic',
                                                                          mnemonic=self.mnemonic))
        continue_button.grid(row=3, column=0)


class WalletCreationVerifyMnemonic(ttk.Frame):

    def __init__(self, root):
        self.root = root
        self.mnemonic = None  # mnemonic will be set from WalletCreationShowMnemonic
        ttk.Frame.__init__(self, self.root.master_frame)

        # attributes defined in gui_draw method
        self.mnemonic_entry = None

    def gui_draw(self):
        title_label = ttk.Label(self, text='Mnemonic Verification:', font=self.root.bold_title_font)
        title_label.grid(row=0, column=0, sticky='n', pady=20)

        mnemonic_entry_label = ttk.Label(self, text='Please enter the mnemonic that you wrote down in the previous '
                                                    'window, to verify that you took it down correctly:',
                                         font=self.root.small_font, justify=tk.CENTER, wrap=520)
        mnemonic_entry_label.grid(row=1, column=0)

        self.mnemonic_entry = tk.Text(self, width=40, height=5, font=self.root.small_font, wrap=tk.WORD)
        self.mnemonic_entry.grid(row=2, column=0, pady=20, columnspan=2)

        button_frame = ttk.Frame(self)

        back_button = ttk.Button(button_frame, text='Back',
                                 command=lambda: self.root.show_frame('WalletCreationShowMnemonic'))
        back_button.grid(row=0, column=0, padx=10)

        continue_button = ttk.Button(button_frame, text='Continue', command=self._on_continue)
        continue_button.grid(row=0, column=1, padx=10)

        button_frame.grid(row=3, column=0, pady=20)

    def _verify_mnemonic(self):
        return self.mnemonic.lower() == self.mnemonic_entry.get(1.0, 'end-1c').strip().lower()

    def _on_continue(self):
        if self._verify_mnemonic():
            self.root.show_frame('MainWallet')
        else:
            messagebox.showerror('Incorrect Entry', 'Mnemonic entered incorrectly, try again.')

            # redraw frame to clear mnemonic entry
            self.root.show_frame('WalletCreationVerifyMnemonic')
