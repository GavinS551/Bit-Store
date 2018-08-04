import base58

from btcpy.structs.transaction import MutableTransaction, MutableSegWitTransaction, TxIn, TxOut, Locktime, Sequence
from btcpy.structs.script import P2pkhScript, P2shScript, Script
from btcpy.structs.sig import ScriptSig, P2pkhSolver
from btcpy.structs.hd import PrivateKey

class Transaction:

    def __init__(self, inputs_amounts, outputs_amounts, change_address,
                 fee, is_segwit, transaction_data, use_least_inputs=True, locktime=0):
        """
        :param inputs_amounts: dict of input addresses and balances (class will chose which ones to use if more than
                                necessary is provided)
        :param outputs_amounts: dict of output addresses and amounts
        :param change_address: change address of txn (will only be used if necessary)
        :param fee: txn fee
        :param is_segwit: bool
        :param transaction_data: unspent_outputs property of wallet class
        :param use_least_inputs: True if the least num of inputs should be spent
        :param locktime: locktime of btc txn
        """

        self.inputs_amounts = inputs_amounts
        self.outputs_amounts = outputs_amounts
        self.change_address = change_address
        self.fee = fee
        self.is_segwit = is_segwit
        self.use_least_inputs = use_least_inputs
        self.locktime = locktime
        self.transaction_data = transaction_data

        self._utxo_data = None

        self.change_amount = 0
        self.chosen_inputs = self._choose_input_addresses()
        self.unsigned_txn = self._get_unsigned_txn()

    @staticmethod
    def _get_pubkey_hash(address):
        return base58.b58decode_check(address)[1:]

    @staticmethod
    def _get_redeemscript_hash(address):
        return base58.b58decode_check(address)[1:]

    def _choose_input_addresses(self):
        """ chose which addresses to spend in txn """
        if self.use_least_inputs:

            total_to_spend = 0
            for i in self.outputs_amounts.values():
                total_to_spend += i
            total_to_spend += self.fee

            if total_to_spend <= 0:
                raise ValueError('amount to send has to be > 0')

            addresses = []
            for address, amount in sorted(self.inputs_amounts.items(),
                                          key=lambda x: x[1], reverse=True):

                addresses.append(address)
                total_to_spend -= amount

                if total_to_spend <= 0:
                    self.change_amount = abs(total_to_spend)
                    return addresses

            # reached if total_to_spend is never <= 0
            raise ValueError('Balances of input address(es) too small for output amount(s)')

        # reserved if another method of choosing inputs is needed
        else:
            raise NotImplementedError

    def _get_unsigned_txn(self):

        # adding change address to outputs, if there is leftover balance
        if self.change_amount > 0:
            self.outputs_amounts[self.change_address] = self.change_amount

        outputs = []
        for i, (addr, amount) in enumerate(self.outputs_amounts.items()):

            if addr[0] == '1':
                outputs.append(TxOut(
                    value=amount,
                    n=i,
                    script_pubkey=P2pkhScript(bytearray(self._get_pubkey_hash(addr)))
                ))

            elif addr[0] == '3':
                outputs.append(TxOut(
                    value=amount,
                    n=i,
                    script_pubkey=P2shScript(bytearray(self._get_redeemscript_hash(addr)))
                ))

            else:
                raise ValueError('Couldn\'t generate a scriptPubKey for entered address')


        if self.is_segwit:
            # PLACEHOLDER
            transaction = MutableSegWitTransaction

        else:

            inputs = []
            for addr in self.chosen_inputs:

                # txn data of particular address
                txn_data = self.transaction_data[addr]

                # list of tuples with txid, output number and address of unspent output
                self._utxo_data = []

                # getting tx ids and output number for all UTXOs to be spent
                for tx in txn_data:

                    txid = tx['hash']
                    # so pycharm will shut up, defining var before loop
                    out_num = None
                    scriptpubkey = None
                    value = None

                    for out in tx['out']:
                        if out['addr'] == addr:
                            out_num = out['n']
                            scriptpubkey = Script.unhexlify(out['script'])
                            value = out['value']
                            break

                    self._utxo_data.append((txid, out_num, addr, scriptpubkey, value))

                for idx in self._utxo_data:

                    inputs.append(

                        TxIn(txid=idx[0],
                             txout=idx[1],
                             script_sig=ScriptSig.empty(),
                             sequence=Sequence.max())
                    )

            transaction = MutableTransaction(
                version=1,
                ins=inputs,
                outs=outputs,
                locktime=Locktime(self.locktime)
            )

        return transaction

    def signed_txn(self, wif_keys):
        """ :param wif_keys: list of wif keys corresponding with
        self.chosen_inputs addresses, in same order
        """
        solvers = []
        tx_outs = []
        unsigned = self.unsigned_txn

        if self.is_segwit:
            pass

        else:
            for key in wif_keys:
                private_key = PrivateKey.from_wif(key)
                solvers.append(P2pkhSolver(private_key))

            addresses_solvers = zip(self.chosen_inputs, solvers)

            for t in self._utxo_data:
                tx_outs.append((t, TxOut(value=t[4], n=t[1], script_pubkey=t[3])))

            def find_solver(address):
                for s in addresses_solvers:
                    if s[0] == address:
                        return s[1]

            _txouts = []
            _solvers = []

            for t in tx_outs:
                address = t[0][2]

                _txouts.append(t[1])
                _solvers.append(find_solver(address))

            signed = unsigned.spend(_txouts, _solvers)

            return signed
