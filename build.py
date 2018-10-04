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
