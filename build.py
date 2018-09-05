""" Windows Only """

import os

os.system(r'py -3.6 -m PyInstaller main.py -w -i lib/gui/assets/bc_logo.ico '
          r'-p lib -F -n Bit-Store.exe --add-data lib/core/wordlist.txt;lib/core '
          r'--add-data lib/gui/assets/bc_logo.ico;lib/gui/assets')
