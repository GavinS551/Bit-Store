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

import json
import functools

from . import utils, _config_vars
from ._config_vars import *


def init():
    """ should be first function called in the program """
    for dir_ in (DATA_DIR, WALLET_DATA_DIR, LOGGER_DIR):
        if not os.path.isdir(dir_):
            os.makedirs(dir_, exist_ok=True)

    # config file init
    if not os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as cf:
            json.dump(DEFAULT_CONFIG, cf, indent=4, sort_keys=False)

    # add new config variables into the file
    missing_vars = set(DEFAULT_CONFIG.keys()) - {k for k in read_file()}
    write_values(**{k: DEFAULT_CONFIG[k] for k in missing_vars})


@functools.lru_cache(maxsize=None)
def read_file():
    try:
        with open(CONFIG_FILE, 'r') as c:
            return json.load(c)
    except FileNotFoundError:
        # when config is imported, and there is no config file,
        # just use what will be dumped into it anyway on init() call
        return DEFAULT_CONFIG


def expected_type(key):
    if key not in DEFAULT_CONFIG:
        raise KeyError(f'{key} is an invalid key')

    return type(DEFAULT_CONFIG[key])


def write_values(**kwargs):
    config = read_file()

    for k, v in kwargs.items():

        if k not in DEFAULT_CONFIG:
            raise KeyError(f'{k} is an invalid key')

        if not isinstance(v, type(DEFAULT_CONFIG[k])):
            raise TypeError(f'{v} is of incorrect type. \'{type(DEFAULT_CONFIG[k])}\' is expected')

        config[k] = v

    data = json.dumps(config, indent=4, sort_keys=True)
    utils.atomic_file_write(data, CONFIG_FILE)


@functools.lru_cache(maxsize=None)
def get(key):
    try:
        return read_file()[key]
    except KeyError:
        if key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]

        elif hasattr(_config_vars, key):
            return getattr(_config_vars, key)

        else:
            raise
