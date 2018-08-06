import base58

from btcpy.structs.transaction import MutableTransaction, MutableSegWitTransaction, TxIn, TxOut, Locktime, Sequence
from btcpy.structs.script import P2pkhScript, P2shScript, Script
from btcpy.structs.sig import ScriptSig, P2pkhSolver
from btcpy.structs.hd import PrivateKey

from .exceptions.tx_exceptions import *


class Transaction:

    def __init__(self, inputs_amounts, outputs_amounts, change_address,
                 fee, is_segwit, utxo_data, locktime=0):
        """
        :param inputs_amounts: dict of input addresses and balances (class will chose which ones to use if more than
                                necessary is provided)
        :param outputs_amounts: dict of output addresses and amounts
        :param change_address: change address of txn (will only be used if necessary)
        :param fee: txn fee
        :param is_segwit: bool
        :param utxo_data: unspent_outputs property of wallet class
        :param locktime: locktime of btc txn
        """

        self.inputs_amounts = inputs_amounts
        self.outputs_amounts = outputs_amounts
        self.change_address = change_address
        self.fee = fee
        self.is_segwit = is_segwit
        self.locktime = locktime
        self.utxo_data = utxo_data


        self.change_amount = 0
        self.chosen_inputs = self._choose_input_addresses()
        self.specific_utxo_data = self._get_specific_utxo_data()
        self.unsigned_txn = self._get_unsigned_txn()

    @staticmethod
    def get_hash160(address):
        """ hash160 of a btc address is the b58_check decoded bytes of the
         address, minus the beginning network byte
         """
        return base58.b58decode_check(address)[1:]

    def _choose_input_addresses(self):
        """ chose which addresses to spend in txn """

        total_to_spend = 0  # total amount of satoshis that will be spent
        for i in self.outputs_amounts.values():
            total_to_spend += i
        total_to_spend += self.fee  # factoring in the fee to the total amount

        if total_to_spend <= 0:
            raise ValueError('amount to send has to be > 0')

        # finds what non-zero int in a list of tuples,
        # where the int is idx [1] in a tuple, is closest to n
        def closest_int(n, list_):
            num_list = [x for _, x in list_]
            m = min(num_list, key=lambda x: abs(x - n))
            if m == 0:
                raise ValueError(f'closest int to {n}, in the list of tuples {list_}, is 0')

            return m

        addresses = []

        # inputs_amounts can be modified without changing class attribute
        inputs_amounts = list(self.inputs_amounts.items())

        # inputs_amounts evaluates to True while it is not empty,
        # when it is empty, all inputs have been added to addresses
        while total_to_spend > 0 and inputs_amounts:

            # finds what input has the closest value to total_to_spend
            closest = list(filter(lambda x: x[1] == closest_int(total_to_spend, inputs_amounts), inputs_amounts))

            # if there are more than 1 tuple that is 'closest', just take the one at [0]
            addresses.append(closest[0][0])
            total_to_spend -= closest[0][1]

            inputs_amounts.remove(closest[0])

        else:
            if total_to_spend <= 0:
                self.change_amount = abs(total_to_spend)
                return addresses
            else:
                raise InsufficientFundsError('Not enough input funds to cover output values')

    def _get_specific_utxo_data(self):
        """ returns the utxo data needed to build signed transactions
         using btcpy's spend() method of MutableTransaction
         """
        utxo_data = []
        for address in self.chosen_inputs:
            for utxo in self.utxo_data:
                if address in utxo:
                    utxo_data.append(utxo)

        return utxo_data

    def _get_unsigned_txn(self):

        TX_VERSION = 1

        # adding change address to outputs, if there is leftover balance
        if self.change_amount > 0:
            self.outputs_amounts[self.change_address] = self.change_amount

        outputs = []
        for i, (addr, amount) in enumerate(self.outputs_amounts.items()):

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

        if self.is_segwit:
            # PLACEHOLDER
            transaction = MutableSegWitTransaction

        else:

            inputs = []

            for t in self.specific_utxo_data:

                # build inputs using the UTXO data in self.specific_utxo_data,
                # script_sig is empty as the transaction will be signed later
                inputs.append(

                    TxIn(txid=t[0],
                         txout=t[1],
                         script_sig=ScriptSig.empty(),
                         sequence=Sequence.max())
                )

            transaction = MutableTransaction(
                version=TX_VERSION,
                ins=inputs,
                outs=outputs,
                locktime=Locktime(self.locktime)
            )

        return transaction

    def signed_txn(self, wif_keys):
        """ :param wif_keys: list of wif keys corresponding with
        self.chosen_inputs addresses, in same order
        """
        unordered_solvers = []
        unordered_tx_outs = []
        unsigned = self.unsigned_txn

        if self.is_segwit:
            pass

        else:
            for key in wif_keys:
                # create btcpy PrivateKeys from input WIF format keys
                private_key = PrivateKey.from_wif(key)
                # create btcpy P2PKH Solvers from those PrivateKeys
                unordered_solvers.append(P2pkhSolver(private_key))

            # a dict that matches the addresses (which are ordered the same as
            # their above WIF Keys) to their solvers
            addresses_solvers = dict(zip(self.chosen_inputs, unordered_solvers))

            # from self.specific_utxo_data, take the output num, value and scriptPubKey
            # and create TxOuts representing the UTXO's that will be spent.
            # In a tuple with the address of the UTXO so the correct solver
            # can be found later
            for t in self.specific_utxo_data:
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

    def change_fee(self, fee):
        self.fee = fee
        # re-run all logic that will be effected by fee change, i.e there might
        # need to be more chosen inputs to make up for the increased fee
        self.chosen_inputs = self._choose_input_addresses()
        self.specific_utxo_data = self._get_specific_utxo_data()
        self.unsigned_txn = self._get_unsigned_txn()

    def validate_transaction(self, tx):
        """ accepts a btcpy txn to compare to class attributes such as the
        outputs, and makes sure they match
        """
        pass
