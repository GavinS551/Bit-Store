import base58

from btcpy.structs.transaction import MutableTransaction, MutableSegWitTransaction, TxIn, TxOut, Locktime, Sequence
from btcpy.structs.script import P2pkhScript, P2shScript, Script, P2wpkhV0Script, ScriptSig
from btcpy.structs.sig import P2pkhSolver, P2shSolver, P2wpkhV0Solver
from btcpy.structs.crypto import PrivateKey

from .structs import UTXOData

from ..exceptions.tx_exceptions import *


class _UTXOChooser:
    """ chooses what utxos to use, to spend {output_amount} """

    def __init__(self, utxos, output_amount, use_unconfirmed=False, use_full_address_utxos=False):
        """
        :param utxos: UTXOs in standard format as shown in blockchain.py
        :param output_amount: amount of satoshis to output
        :param use_unconfirmed: should unconfirmed UTXO's be chosen
        :param use_full_address_utxos: should all of an addresses UTXOs be chosen, and not cherry-picked
        """

        self._utxos = [UTXOData(*utxo) for utxo in utxos]
        self._output_amount = output_amount
        self._use_unconfirmed = use_unconfirmed
        self._use_full_address_utxos = use_full_address_utxos

        if not self._use_unconfirmed:
            self._remove_unconfirmed()

        self.change_amount = None
        self.chosen_utxos = None
        self.chosen_addresses = None

        self._choose_utxos()

    def _remove_unconfirmed(self):
        self._utxos = [u for u in self._utxos if u.is_confirmed()]

    @property
    def _addresses(self):
        """ returns all addresses associated with all utxos """
        addresses = []

        for u in self._utxos:
            if u.address not in addresses:
                addresses.append(u.address)

        return addresses

    @staticmethod
    def _closest_int(int_list, n):
        """ finds what non-zero int in int_list is closest to n """
        non_zero_list = [i for i in int_list if i > 0]
        m = min(non_zero_list, key=lambda x: abs(x - n))
        return m

    def _find_closest_value_utxo(self, value):
        """ finds what utxo has a value closest to passed value"""
        utxo_values = [u.value for u in self._utxos]
        closest_value = self._closest_int(utxo_values, value)

        for u in self._utxos:
            if u.value == closest_value:
                return u

    def _get_address_utxos(self, address):
        """ returns all utxos associated with a particular address """
        utxos = [u for u in self._utxos if u.address == address]
        return utxos

    def _find_closest_value_address_utxos(self, value):
        """ finds what utxos, grouped by address, has closest total value to passed value"""

        # initialising dict
        address_balances = dict.fromkeys(self._addresses, 0)

        # adding up all address balances
        for u in self._utxos:
            address_balances[u.address] += u.value

        # making it into list so the keys can be found by values
        address_balances_list = list(address_balances.items())

        # list of the values to be passed into closest_int method
        address_values = [v for _, v in address_balances_list]

        closest_value = self._closest_int(address_values, value)

        # if there is more than 1 address returned by the list comprehension,
        # just take the first element as the value is the only important thing
        closest_address = [a for a, v in address_balances_list if v == closest_value][0]

        return self._get_address_utxos(closest_address)

    def _choose_utxos(self):

        chosen_utxos = []
        output_amount = self._output_amount

        while output_amount > 0 and self._utxos:

            if self._use_full_address_utxos is True:
                closest = self._find_closest_value_address_utxos(output_amount)

                # closest is a list of utxos in this case
                for u in closest:
                    output_amount -= u.value
                    chosen_utxos.append(u)

                    self._utxos.remove(u)

            else:
                closest = self._find_closest_value_utxo(output_amount)

                output_amount -= closest.value
                chosen_utxos.append(closest)

                self._utxos.remove(closest)

        else:
            if output_amount > 0:
                raise InsufficientFundsError(f'Not enough UTXO value to match output amount. '
                                             f'{output_amount} satoshis more needed')

            else:
                # change amount is the "overflow" satoshis after choosing utxos
                self.change_amount = abs(output_amount)

                standard_format_utxos = [u.standard_format for u in chosen_utxos]
                self.chosen_utxos = standard_format_utxos

                addresses = []
                for u in chosen_utxos:
                    # makes sure addresses aren't repeated
                    if u.address not in addresses:
                        addresses.append(u.address)

                self.chosen_addresses = addresses


class Transaction:

    def __init__(self, utxo_data, outputs_amounts, change_address,
                 fee, is_segwit, locktime=0,
                 use_unconfirmed_utxos=False,
                 use_full_address_utxos=True):
        """
        :param utxo_data: list of unspent outs in standard format. which ones to be spend will be chosen in class
        :param outputs_amounts: dict of output addresses and amounts
        :param change_address: change address of txn (if needed)
        :param fee: txn fee
        :param is_segwit: bool
        :param locktime: locktime of btc txn
        :param use_unconfirmed_utxos: should unconfirmed UTXO's be chosen
        :param use_full_address_utxos: should all of an addresses UTXOs be chosen, and not cherry-picked
        """

        self._outputs_amounts = outputs_amounts
        self._change_address = change_address
        self._locktime = locktime
        self._utxo_data = utxo_data

        assert self._change_address not in outputs_amounts

        self._use_unconfirmed_utxos = use_unconfirmed_utxos
        self._use_full_address_utxos = use_full_address_utxos

        self.fee = fee
        self.is_segwit = is_segwit
        self.is_signed = False

        # these 3 attributes will be set by _choose_utxos method
        self._change_amount = None
        self.input_addresses = None
        self._specific_utxo_data = None

        self._choose_utxos()

        self._unsigned_txn = self._get_unsigned_txn()

        # can be used to determine correct fees for transaction
        self.size = self._unsigned_txn.size
        self.weight = self._unsigned_txn.weight

        self.txn = self._unsigned_txn

    @staticmethod
    def get_hash160(address):
        """ hash160 of a btc address is the b58_check decoded bytes of the
         address, minus the beginning network byte
         """
        return base58.b58decode_check(address)[1:]

    def _choose_utxos(self):
        output_amount = sum([v for v in self._outputs_amounts.values()]) + self.fee

        chooser = _UTXOChooser(utxos=self._utxo_data,
                               output_amount=output_amount,
                               use_unconfirmed=self._use_unconfirmed_utxos,
                               use_full_address_utxos=self._use_full_address_utxos)

        self._change_amount = chooser.change_amount
        self.input_addresses = chooser.chosen_addresses
        self._specific_utxo_data = chooser.chosen_utxos

    def _get_unsigned_txn(self):

        TX_VERSION = 1

        # outputs_amounts is copied so any instance can be modified with change_fee,
        # and will still function correctly, i.e the change address won't already
        # be in the self._outputs_amounts dict
        outputs_amounts = self._outputs_amounts.copy()

        # adding change address to outputs, if there is leftover balance
        if self._change_amount > 0:
            outputs_amounts[self._change_address] = self._change_amount

        outputs = []
        for i, (addr, amount) in enumerate(outputs_amounts.items()):

            # normal, P2PKH btc addresses begin with '1'
            if addr[0] == '1':
                out_script = P2pkhScript

            # and P2SH addresses begin with '3' (applies to non-native segwit addresses as well)
            elif addr[0] == '3':
                out_script = P2shScript

            else:
                raise ValueError('Couldn\'t generate a scriptPubKey for entered address')

            outputs.append(TxOut(
                value=amount,
                n=i,
                script_pubkey=out_script(bytearray(self.get_hash160(addr)))
            ))

        inputs = []

        for t in self._specific_utxo_data:

            # build inputs using the UTXO data in self._specific_utxo_data,
            # script_sig is empty as the transaction will be signed later
            inputs.append(

                TxIn(txid=t[0],
                     txout=t[1],
                     script_sig=ScriptSig.empty(),
                     sequence=Sequence.max())
            )

        if self.is_segwit:

            transaction = MutableSegWitTransaction(
                version=TX_VERSION,
                ins=inputs,
                outs=outputs,
                locktime=Locktime(self._locktime)
            )

        else:

            transaction = MutableTransaction(
                version=TX_VERSION,
                ins=inputs,
                outs=outputs,
                locktime=Locktime(self._locktime)
            )

        return transaction

    def _get_signed_txn(self, wif_keys):
        """ :param wif_keys: list of wif keys corresponding with
        self.input_addresses addresses, in same order
        """
        unordered_solvers = []
        unordered_tx_outs = []
        unsigned = self._unsigned_txn

        for key in wif_keys:
            # create btcpy PrivateKeys from input WIF format keys
            private_key = PrivateKey.from_wif(key)

            if self.is_segwit:
                pub_key = private_key.pub(compressed=True)

                s_solver = P2shSolver(
                    P2wpkhV0Script(pub_key),
                    P2wpkhV0Solver(private_key)
                )

                unordered_solvers.append(s_solver)
            else:
                # create btcpy P2PKH Solvers from those PrivateKeys
                unordered_solvers.append(P2pkhSolver(private_key))

        # a dict that matches the addresses (which are ordered the same as
        # their above WIF Keys) to their solvers
        addresses_solvers = dict(zip(self.input_addresses, unordered_solvers))

        # from self._specific_utxo_data, take the output num, value and scriptPubKey
        # and create TxOuts representing the UTXO's that will be spent.
        # In a tuple with the address of the UTXO so the correct solver
        # can be found later
        for t in self._specific_utxo_data:
            unordered_tx_outs.append((t[2], TxOut(value=t[4], n=t[1], script_pubkey=Script.unhexlify(t[3]))))

        # unlike the lists defined at the top of the method, these are in
        # order i.e the solver in solvers[0] is the solver for the TxOut of
        # tx_outs[0]. this is required to pass them into the spend() method
        tx_outs = []
        solvers = []

        for t in unordered_tx_outs:
            address = t[0]

            tx_outs.append(t[1])
            solvers.append(addresses_solvers[address])

        signed = unsigned.spend(tx_outs, solvers)

        return signed

    def sign(self, wif_keys):
        self.txn = self._get_signed_txn(wif_keys)
        self.is_signed = True

    def change_fee(self, fee):
        self.fee = fee
        # re-run all logic that will be effected by fee change, i.e there might
        # need to be more chosen inputs to make up for the increased fee
        self._choose_utxos()
        self.txn = self._get_unsigned_txn()
        self.is_signed = False
