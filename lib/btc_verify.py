""" ADAPTED FROM: https://rosettacode.org/wiki/Bitcoin/address_validation#Python """

from hashlib import sha256

from base58 import alphabet


def decode_base58(bc, length):
    n = 0
    for char in bc:
        n = n * 58 + alphabet.index(char)
    return n.to_bytes(length, 'big')


def check_bc(bc):
    if isinstance(bc, list):
        valid_list = []
        try:

            for a in bc:
                bcbytes = decode_base58(a, 25)
                valid_list.append(bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4])

            return all(valid_list)

        except Exception:
            return False
    else:

        try:
            bcbytes = decode_base58(bc, 25)
            return bcbytes[-4:] == sha256(sha256(bcbytes[:-4]).digest()).digest()[:4]

        except Exception:
            return False
