""" miscellaneous functions and classes used in the program """

import os
import decimal
from functools import wraps
from threading import Thread
from queue import Empty
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


def validate_address(address):
    """ function that validates a btc address """
    try:
        base58.b58decode_check(address)
        return True
    except ValueError:
        return False


def validate_addresses(addresses):
    """ function that validates a list of btc addresses"""
    return all(validate_address(a) for a in addresses)


def float_to_str(float_):
    """ Convert the given float to a string, without scientific notation """
    with decimal.localcontext() as ctx:
        d1 = ctx.create_decimal(repr(float_))
        return format(d1, 'f')


def find_key_from_value(dict_, value):
    """ returns the (first) matching key in a dict for a given value """
    for k, v in dict_.items():
        if v == value:
            return k


class IterableQueue:

    def __init__(self, queue):
        self.queue = queue

    def __iter__(self):
        while True:
            try:
                yield self.queue.get_nowait()
            except Empty:
                break
