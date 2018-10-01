import tkinter as tk
from tkinter import ttk

import qrcode
from PIL import ImageTk


class ReceiveDisplay(ttk.Frame):

    def __init__(self, master, main_wallet):
        ttk.Frame.__init__(self, master, padding=5)
        self.main_wallet = main_wallet

        self.grid_rowconfigure(0, {'minsize': 10})

        self.address_label = ttk.Label(self, text='Receiving Address:',
                                       font=self.main_wallet.root.small_font + ('bold',))
        self.address_label.grid(row=1, column=0, sticky='w', padx=10)

        self.address_text = tk.Text(self, height=1, width=40, font=self.main_wallet.root.small_font,
                                    state=tk.DISABLED)
        self.address_text.configure(inactiveselectbackground=self.address_text.cget("selectbackground"))
        self.address_text.grid(row=1, column=1, padx=20)

        self.qr = None
        self.qr_label = None
        self.draw_qr_code()

        self._update_address()

    def _update_address(self):
        """ a text widget is used for address display as it is copyable, however
         it doesn't have a textvariable param so the address is updated here
        """
        # if the address has changed, then update text
        if self.address_text.get(1.0, 'end-1c') != self.main_wallet.next_receiving_address.get():
            self.address_text['state'] = tk.NORMAL

            self.address_text.delete(1.0, tk.END)
            self.address_text.insert(tk.END, self.main_wallet.next_receiving_address.get())

            self.address_text['state'] = tk.DISABLED

            # update qr code with new address
            self.draw_qr_code()

        self.main_wallet.root.after(self.main_wallet.refresh_data_rate, self._update_address)

    def _make_qr_code(self):
        qr = qrcode.QRCode(box_size=5)
        qr.add_data(self.main_wallet.next_receiving_address.get())

        bg_colour = '#DCDAD5' if self.main_wallet.root.theme == 'clam' else '#F0F0F0'
        tk_image = ImageTk.PhotoImage(qr.make_image(back_color=bg_colour))
        return tk_image

    def draw_qr_code(self):
        # keep reference to image or it will be garbage collected
        self.qr = self._make_qr_code()
        self.qr_label = ttk.Label(self, image=self.qr)
        self.qr_label.grid(row=1, column=2)

    @property
    def address(self):
        return self.address_text.get(1.0, 'end-1c')

    def on_copy(self):
        self.main_wallet.root.clipboard_clear()
        self.main_wallet.root.clipboard_append(self.address)
