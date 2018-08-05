import base58

from btcpy.structs.transaction import MutableTransaction, MutableSegWitTransaction, TxIn, TxOut, Locktime, Sequence
from btcpy.structs.script import P2pkhScript, P2shScript, Script
from btcpy.structs.sig import ScriptSig, P2pkhSolver
from btcpy.structs.hd import PrivateKey

class Transaction:

    def __init__(self, inputs_amounts, outputs_amounts, change_address,
                 fee, is_segwit, transaction_data, locktime=0):
        """
        :param inputs_amounts: dict of input addresses and balances (class will chose which ones to use if more than
                                necessary is provided)
        :param outputs_amounts: dict of output addresses and amounts
        :param change_address: change address of txn (will only be used if necessary)
        :param fee: txn fee
        :param is_segwit: bool
        :param transaction_data: unspent_outputs property of wallet class
        :param locktime: locktime of btc txn
        """

        self.inputs_amounts = inputs_amounts
        self.outputs_amounts = outputs_amounts
        self.change_address = change_address
        self.fee = fee
        self.is_segwit = is_segwit
        self.locktime = locktime
        self.transaction_data = transaction_data

        self._utxo_data = self._get_utxo_data()

        self.change_amount = 0
        self.chosen_inputs = self._choose_input_addresses()
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

        addresses = []
        # sorts the input addresses by biggest to smallest, so the least amount
        # of inputs are spent for the transaction
        for address, amount in sorted(self.inputs_amounts.items(),
                                      key=lambda x: x[1], reverse=True):

            addresses.append(address)
            total_to_spend -= amount

            if total_to_spend <= 0:
                # the leftover change will be sent to the provided change address later
                self.change_amount = abs(total_to_spend)
                return addresses

        # reached if total_to_spend is never <= 0
        raise ValueError('Balances of input address(es) too small for output amount(s)')

    def _get_utxo_data(self):
        """ returns the utxo data needed to build signed transactions
         using btcpy's spend() method of MutableTransaction
         """
        utxo_data = []
        for addr in self.chosen_inputs:

            # txn data of particular address
            txn_data = self.transaction_data[addr]

            # getting tx ids and output number for all UTXOs to be spent
            for tx in txn_data:

                # getting the transaction id
                txid = tx['hash']

                # variables will be None if they aren't assigned in below loop
                out_num = None
                scriptpubkey = None
                value = None

                for out in tx['out']:
                    if out['addr'] == addr:
                        out_num = out['n']
                        scriptpubkey = Script.unhexlify(out['script'])
                        value = out['value']  # value of output in satoshis
                        break

                utxo_data.append((txid, out_num, addr, scriptpubkey, value))

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

            for t in self._utxo_data:

                # build inputs using the UTXO data in self._utxo_data,
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

            # from self._utxo_data, take the output num, value and scriptPubKey
            # and create TxOuts representing the UTXO's that will be spent.
            # In a tuple with the address of the UTXO so the correct solver
            # can be found later
            for t in self._utxo_data:
                unordered_tx_outs.append((t[2], TxOut(value=t[4], n=t[1], script_pubkey=t[3])))

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
