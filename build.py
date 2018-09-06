import os
import platform
import sys


if __name__ == '__main__':

    if platform.system() == 'Windows':
        os.system(f'"{sys.executable}" -m PyInstaller main.py -w -i lib/gui/assets/bc_logo.ico '
                  '-p lib -F -n Bit-Store.exe --add-data lib/core/wordlist.txt;lib/core '
                  '--add-data lib/gui/assets/bc_logo.ico;lib/gui/assets')

    elif platform.system() in ('Linux', 'Darwin'):
        os.system(f'"{sys.executable}" -m PyInstaller main.py -w -i lib/gui/assets/bc_logo.ico '
                  '-p lib -F -n Bit-Store --add-data lib/core/wordlist.txt:lib/core '
                  '--add-data lib/gui/assets/bc_logo.ico:lib/gui/assets --hidden-import="PIL._tkinter_finder"')
