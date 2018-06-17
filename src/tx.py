import btcpy.structs.transaction as btc_tx


class Transaction:

    def __init__(self, senders_amounts, receivers_amounts, change_address,
                 fee, is_segwit, use_least_inputs=True):
        """
        :param senders_amounts: dict of sender addresses and balances
        :param receivers_amounts: dict of receiving addresses and amounts
        :param change_address: change address of txn
        :param fee: txn fee
        :param segwit: bool
        :param use_least_inputs: True if the least num of inputs should be spent
        """

        self.senders_amounts = senders_amounts
        self.receivers_amounts = receivers_amounts
        self.change_address = change_address
        self.fee = fee
        self.is_segwit = is_segwit
        self.use_least_inputs = use_least_inputs

        self.is_signed = False
        self.chosen_inputs = self._choose_input_addresses()

    def _choose_input_addresses(self):
        """ chose which addresses to spend in txn """
        if self.use_least_inputs:

            total_to_send = 0
            for i in self.receivers_amounts.values():
                total_to_send += i

            if total_to_send <= 0:
                raise ValueError('amount to send has to be > 0')

            addresses = []
            for address, amount in sorted(self.senders_amounts.items(),
                                          key=lambda x: x[1], reverse=True):

                addresses.append(address)
                total_to_send -= amount

                if total_to_send <= 0:
                    return addresses

            # reached if total_to_send is never <= 0
            raise ValueError('Balances of input address(es) too small for output amount(s)')

        else:
            raise NotImplementedError

    def _make_txn(self):
        pass

    def sign(self):
        pass


if __name__ == '__main__':
    tx = Transaction({'1': 123124, '2': 900000, '3': 1001}, {'878': 123125, '234': 10}, 1, 1)
    tx._choose_input_addresses()
    print(tx._choose_input_addresses())
