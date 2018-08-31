BIT-STORE BITCOIN WALLET


LIMITATIONS:

> if 2 transactions are made within ~ 5 seconds of each other, there is a chance they will both use the same change address.
This shouldn't be an issue as you can send to multiple different addresses per transaction

> only a maximum of 100 transactions can be shown due to limits with the blockchain.info api. Therefore only balances
associated with those 100 transactions can be shown. This is to avoid confusion, e.g. if wallet balance was shown independent of transactions,
and you have 120 transactions, but your wallet balance is showing you have 2 BTC. You may not be able to spend those 2 BTC as the unspent outputs
that add up to that 2 BTC balance may be at the 105th transaction


STANDARD DATA FORMATS:

When standard format is mentioned in this project, it is referring to how unspent outputs and transactions
are stored.

Transactions:  {

            'txid': str,
            'date': str,
            'block_height': int,
            'confirmations': int,
            'fee': int,
            'vsize': int,
            'inputs': [{'value': int, 'address': str, 'n': int}, ...],
            'outputs': [{'value': int, 'address': str, 'n': int, 'spent': bool}, ...],
            'wallet_amount': int

        }


Unspent Outputs: [txid, output_num, address, script, value, confirmations]
(the UTXOData class in structs.py can make using this data easier, e.g  referring to txid as utxo.txid vs utxo[0])