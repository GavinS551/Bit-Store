""" miscellaneous functions and classes used in the program """

import os
import decimal
import datetime
from functools import wraps
from threading import Thread
from queue import Empty
from contextlib import suppress

import base58


def atomic_file_write(data: str, file_path: str):
    """ atomically write data (string) to a file """

    tmp_file = file_path + '.tmp'
    with open(tmp_file, 'w') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_file, file_path)


def threaded(func=None, daemon=False, name=None):
    """ wrapper that returns a thread handle with its target set to wrapped function """
    def decorator(func_):

        @wraps(func_)
        def wrapped(*args, **kwargs):
            t = Thread(target=func_, args=args, kwargs=kwargs, daemon=daemon, name=name)
            t.start()
            return t

        return wrapped

    if func:
        return decorator(func)

    return decorator


def validate_address(address, allow_testnet=False):
    """ function that validates a btc address """
    possible_network_bytes = (0x00, 0x05)

    if allow_testnet:
        possible_network_bytes += (0x6F, 0xC4)

    with suppress(ValueError):
        if base58.b58decode_check(address)[0] in possible_network_bytes:
            return True

    return False


def validate_addresses(addresses):
    """ function that validates a list of btc addresses"""
    return all(validate_address(a) for a in addresses)


def float_to_str(float_, show_plus_sign=False):
    """ Convert the given float to a string, without scientific notation """
    with decimal.localcontext() as ctx:
        d1 = ctx.create_decimal(repr(float_))
        if not show_plus_sign or format(d1, 'f')[0] == '-':
            return format(d1, 'f')

        else:
            return '+' + format(d1, 'f')


def datetime_str_from_timestamp(timestamp, fmt, utc=True):
    """ converts a unix timestamp to a datetime string. Uses local time if utc is false """

    utc_datetime = datetime.datetime.utcfromtimestamp(timestamp)
    if utc:
        return utc_datetime.strftime(fmt)
    else:
        local_datetime = utc_datetime.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        return local_datetime.strftime(fmt)


class IterableQueue:

    def __init__(self, queue):
        self.queue = queue

    def __iter__(self):
        while True:
            try:
                yield self.queue.get_nowait()
            except Empty:
                break
