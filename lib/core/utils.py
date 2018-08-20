import os
import decimal
from functools import wraps
from threading import Thread

import base58


def atomic_file_write(data: str, file_path: str):
    """ atomically write data (string) to a file """

    tmp_file = file_path + '.tmp'
    with open(tmp_file, 'w') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp_file, file_path)


def threaded(func=None, daemon=False):
    """ wrapper that returns a thread handle with its target set to wrapped function """
    def decorator(func_):

        @wraps(func_)
        def wrapped(*args, **kwargs):
            t = Thread(target=func_, args=args, kwargs=kwargs, daemon=daemon)
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
