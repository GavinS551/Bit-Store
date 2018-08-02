""" Taken from <https://tinyurl.com/y7tq3963> """
import sys
import ctypes
import platform


# this function does not work in threads, so it is not in use currently
# TODO: get it working


def zeromem(string):
    if platform.system() == 'Windows':
        location = id(string) + 20
        size = sys.getsizeof(string) - 20

        memset = ctypes.cdll.msvcrt.memset
        # For Linux, use the following. Change the 6 to whatever it is on your computer.
        # memset =  ctypes.CDLL("libc.so.6").memset

        memset(location, 0, size)

    else:
        print('"zero_mem.py": This feature is only supported on Windows')
