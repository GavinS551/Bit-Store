import unittest

from src.bip32 import *

mnemonic = 'tiny useless make elegant meadow lobster clown record buzz goddess rookie purity'
bip32 = Bip32.from_mnemonic(mnemonic)


class Bip32Test(unittest.TestCase):

    def test_mnemonic_store(self):
        self.assertEqual(bip32.mnemonic, mnemonic)

    def test_segwit_address_generation(self):
        if bip32.segwit or bip32.path == bip32.PATHS['bip49path']:
            self.assertEqual(bip32.addresses()[0][0][0], '3')
        else:
            self.assertEqual(bip32.addresses()[0][0][0], '1')


if __name__ == '__main__':
    unittest.main()
