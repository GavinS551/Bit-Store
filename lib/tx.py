import base58

from btcpy.structs.transaction import MutableTransaction, MutableSegWitTransaction, TxIn, TxOut, Locktime, Sequence
from btcpy.structs.script import P2pkhScript, P2shScript
from btcpy.structs.sig import ScriptSig


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

        self.change_amount = 0
        self.chosen_inputs = self._choose_input_addresses()

    @staticmethod
    def _get_pubkey_hash(address):
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

    @property
    def unsigned_txn(self):

        # adding change address to outputs, if there is leftover balance
        if self.change_amount > 0:
            self.outputs_amounts[self.change_address] = self.change_amount

        outputs = []
        for i, (addr, amount) in enumerate(self.outputs_amounts.items()):

            if addr[0] == '1':
                out_script = P2pkhScript
            elif addr[0] == '3':
                out_script = P2shScript
            else:
                raise ValueError('Couldn\'t generate a scriptPubKey for entered address')

            outputs.append(TxOut(
                value=amount,
                n=i,
                script_pubkey=out_script(bytearray(self._get_pubkey_hash(addr)))
            ))

        if self.is_segwit:
            # PLACEHOLDER
            transaction = MutableSegWitTransaction

        else:

            inputs = []
            for addr in self.chosen_inputs:

                # txn data of particular address
                txn_data = self.transaction_data[addr]

                # list of tuples with txid, output number and address of unspent output
                tx_ids_out_num = []

                # getting tx ids and output number for all UTXOs to be spent
                for tx in txn_data:

                    txid = tx['hash']
                    out_num = None  # so pycharm will shut up, defining var before loop

                    for out in tx['out']:
                        if out['addr'] == addr:
                            out_num = out['n']
                            break

                    tx_ids_out_num.append((txid, out_num, addr))

                for idx in tx_ids_out_num:

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
