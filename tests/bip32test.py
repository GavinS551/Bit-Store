import unittest

from src.bip32 import *


class Bip32Test(unittest.TestCase):

    mnemonic = 'tiny useless make elegant meadow lobster clown record buzz goddess rookie purity'
    xpriv = 'xprv9s21ZrQH143K3ZeMhMr7tjcoxDGB7CZVPkoYkBo4ERJqVRm7vJAtovk8DRPar9rjsEjGWB4K928yLKF4by8EhsgkPAkhEUifYDkFjcp2axR'
    xpub = 'xpub661MyMwAqRbcG3ipoPP8FsZYWF6fWfHLkyj9YaCfnkqpNE6GTqV9Mj4c4idh2KDGxL3EGDtnSj8Zn7MPBGs6vqVzD9QKx5iGTFM6Vvk9qoF'
    a_xpub = 'xpub6DAHMvkS7fbyKTFPNDjuR9F4jeRSWpb5h2k23U2ADBwqjbkvZzfhdAkSxqoi6xap7jnrJJKpRE29Uma8ojc6Wi9L1T3KH1NmPrigShWic9Z'

    testnet_xpriv = 'tprv8ZgxMBicQKsPf1JghXWoPtq8oDGvivqc9RV7gBhMUNmcvhx9dKsLN2iJesGBrCqhG3oKJUhmKpZnzfL5zzffvExP8NMCDgTAsnTdCD1MJcG'
    bip32 = Bip32.from_mnemonic(mnemonic)
    t_bip32 = Bip32(key=testnet_xpriv)

    def test_segwit_address_generation(self):
        if self.bip32.segwit and not self.bip32.is_testnet:
            self.assertEqual(self.bip32.addresses()[0][0][0], '3')
        else:
            self.assertEqual(self.bip32.addresses()[0][0][0], '1')

    def test_testnet_xkey_recognition(self):
        self.assertEqual(self.t_bip32.is_testnet, True)
        # test to see if it produces testnet addresses as well
        if self.t_bip32.segwit:
            self.assertEqual(self.t_bip32.addresses()[0][0][0], '2')
        else:
            self.assertEqual(self.t_bip32.addresses()[0][0][0], 'n' or 'm')

    def test_key_derivation(self):
        self.assertEqual(self.bip32.master_private_key, self.xpriv)
        self.assertEqual(self.bip32.master_public_key, self.xpub)
        self.assertEqual(self.bip32.account_public_key, self.a_xpub)

    def test_wifkey_address_matchup(self):
        self.assertEqual(len(self.bip32.addresses()[0]), len(self.bip32.wif_keys()[0]))  # receiving addresses/wifkeys
        self.assertEqual(len(self.bip32.addresses()[1]), len(self.bip32.wif_keys()[1]))  # change addresses/wifkeys

    def test_check_mnemonic(self):
        self.assertTrue(self.bip32.check_mnemonic(self.bip32.mnemonic))
        self.assertFalse(self.bip32.check_mnemonic('TOTALLY NOT A MNEMONIC'))


if __name__ == '__main__':
    unittest.main()
