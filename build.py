import os
import platform

if platform.system() == 'Windows':
    os.system(r'py -3.6 -m PyInstaller main.py -w -i lib/gui/assets/bc_logo.ico '
              r'-p lib -F -n Bit-Store.exe --add-data lib/core/wordlist.txt;lib/core '
              r'--add-data lib/gui/assets/bc_logo.ico;lib/gui/assets')

elif platform.system() == 'Linux':
    os.system(r'python3.6 -m PyInstaller main.py -w -i lib/gui/assets/bc_logo.ico '
              r'-p lib -F -n Bit-Store --add-data lib/core/wordlist.txt:lib/core '
              r'--add-data lib/gui/assets/bc_logo.ico:lib/gui/assets --hidden-import="PIL._tkinter_finder"')
