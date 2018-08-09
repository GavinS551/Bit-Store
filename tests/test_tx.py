import pytest

from lib.tx import Transaction, _UTXOChooser, InsufficientFundsError


TEST_UTXO_CHOOSER_UTXOS = [
    ['hash', 0, '369mnsgVivq1Dq2aep1RsSx4fz39kEzVMi', 'script', 1, 0],
    ['hash', 0, '369mnsgVivq1Dq2aep1RsSx4fz39kEzVMi', 'script', 124122323, 0],
    ['hash', 0, '369mnsgVivq1Dq2aep1RsSx4fz39kEzVMi', 'script', 4, 45],
    ['hash', 0, '3NcRENt1SwsbZBdZd1sLMXgtXXVBXFA4aA', 'script', 876, 1],
    ['hash', 0, '3JQrxCwiKLLM8VNCfddiMiM8e5Vm4cgwiz', 'script', 235763312, 120002],
    ['hash', 0, '39HzCLXazJrsuVeBkRFUnSHbvxUzohjECT', 'script', 346343, 0]
]


def test_utxo_chooser():

    chooser_default_expected = [['hash', 0, '3NcRENt1SwsbZBdZd1sLMXgtXXVBXFA4aA', 'script', 876, 1], ['hash', 0, '369mnsgVivq1Dq2aep1RsSx4fz39kEzVMi', 'script', 4, 45], ['hash', 0, '3JQrxCwiKLLM8VNCfddiMiM8e5Vm4cgwiz', 'script', 235763312, 120002]]
    chooser_unconfirmed_expected = [['hash', 0, '3NcRENt1SwsbZBdZd1sLMXgtXXVBXFA4aA', 'script', 876, 1], ['hash', 0, '369mnsgVivq1Dq2aep1RsSx4fz39kEzVMi', 'script', 4, 45], ['hash', 0, '369mnsgVivq1Dq2aep1RsSx4fz39kEzVMi', 'script', 1, 0], ['hash', 0, '39HzCLXazJrsuVeBkRFUnSHbvxUzohjECT', 'script', 346343, 0]]
    chooser_use_full_addresses_expected = [['hash', 0, '3NcRENt1SwsbZBdZd1sLMXgtXXVBXFA4aA', 'script', 876, 1], ['hash', 0, '39HzCLXazJrsuVeBkRFUnSHbvxUzohjECT', 'script', 346343, 0]]


    chooser_default = _UTXOChooser(TEST_UTXO_CHOOSER_UTXOS, 100000)
    chooser_unconfirmed = _UTXOChooser(TEST_UTXO_CHOOSER_UTXOS, 100000, use_unconfirmed=True)
    chooser_use_full_addresses = _UTXOChooser(TEST_UTXO_CHOOSER_UTXOS, 100000, use_full_address_utxos=True, use_unconfirmed=True)

    assert chooser_default.chosen_utxos == chooser_default_expected
    assert chooser_unconfirmed.chosen_utxos == chooser_unconfirmed_expected
    assert chooser_use_full_addresses.chosen_utxos == chooser_use_full_addresses_expected

    assert chooser_default.change_amount == 235664192
    assert chooser_unconfirmed.change_amount == 247224
    assert chooser_use_full_addresses.change_amount == 247219

    with pytest.raises(InsufficientFundsError):
        _UTXOChooser(TEST_UTXO_CHOOSER_UTXOS, 100000000000000000)


def _make_utxos(addresses):
    utxos = []
    for i, a in enumerate(addresses):
        utxos.append(['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733',
                      0, a, 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', i**10, i])
    return utxos


def test_transaction():
    transaction_test_utxos = _make_utxos(['38Lw1zoLuDwpqkwNrKiSUwsY8Psnqfa39n',
                                          '3DuK9rcspGTNofSkekk4Zbx1XHMqjS5E7N',
                                          '3EgW5UCtPhR5N7efdC2DXspDxZRGxJiT77',
                                          '38CsFpFDNqV9t7wBUTgLoLpFzswNTkHKck'])

    output_amounts = {
        '36bB5ZCb9GXTDAUgVbotGtFpncwurTL5CP': 102,
        '3CVJDmtREsF2VG16WqfzHqrcc6uYF6dVfe': 21533
    }

    transaction = Transaction(transaction_test_utxos, output_amounts,
                              '36GKcc8qfN3nYJvAveHYekgwnzdyn72and', 2142, True)

    s_txn = "SegWitTransaction(version=1, ins=[TxIn(txid=b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733, txout=0, script_sig=, sequence=4294967295, witness=None), TxIn(txid=b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733, txout=0, script_sig=, sequence=4294967295, witness=None), TxIn(txid=b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733, txout=0, script_sig=, sequence=4294967295, witness=None)], outs=[TxOut(value=102, n=0, scriptPubKey='OP_HASH160 35bdc692c8ff698a482a5bec793ab28bd475dd8c OP_EQUAL'), TxOut(value=21533, n=1, scriptPubKey='OP_HASH160 7671ff0719b289944ce871df51b6d5fe4ab02a7f OP_EQUAL'), TxOut(value=36297, n=2, scriptPubKey='OP_HASH160 322cff52ece9716c1e4464bef9e8f2fea14b524d OP_EQUAL')], locktime=Locktime(0))"
    assert str(transaction.txn) == s_txn
    assert transaction.fee == 2142
    assert transaction.input_addresses == ['3EgW5UCtPhR5N7efdC2DXspDxZRGxJiT77', '3DuK9rcspGTNofSkekk4Zbx1XHMqjS5E7N', '38CsFpFDNqV9t7wBUTgLoLpFzswNTkHKck']
    assert transaction._change_amount == 36297
    assert transaction._specific_utxo_data == [['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733', 0, '3EgW5UCtPhR5N7efdC2DXspDxZRGxJiT77', 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', 1024, 2], ['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733', 0, '3DuK9rcspGTNofSkekk4Zbx1XHMqjS5E7N', 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', 1, 1], ['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733', 0, '38CsFpFDNqV9t7wBUTgLoLpFzswNTkHKck', 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', 59049, 3]]
    assert transaction.size == 229
    assert transaction.weight == 916

    assert transaction.get_hash160('36GKcc8qfN3nYJvAveHYekgwnzdyn72and').hex() == '322cff52ece9716c1e4464bef9e8f2fea14b524d'

    transaction.change_fee(1135)

    assert transaction.fee == 1135
    assert transaction.input_addresses == ['3EgW5UCtPhR5N7efdC2DXspDxZRGxJiT77', '3DuK9rcspGTNofSkekk4Zbx1XHMqjS5E7N', '38CsFpFDNqV9t7wBUTgLoLpFzswNTkHKck']
    assert transaction._change_amount == 37304
    assert transaction._specific_utxo_data == [['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733', 0, '3EgW5UCtPhR5N7efdC2DXspDxZRGxJiT77', 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', 1024, 2], ['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733', 0, '3DuK9rcspGTNofSkekk4Zbx1XHMqjS5E7N', 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', 1, 1], ['b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733', 0, '38CsFpFDNqV9t7wBUTgLoLpFzswNTkHKck', 'a9147671ff0719b289944ce871df51b6d5fe4ab02a7f87', 59049, 3]]
    assert transaction.size == 229
    assert transaction.weight == 916

    private_keys = ['L2vZ3TXfw5FTE7raJYTp3CBcwChY6bV5nbnnGifHFv6GoGRfdNhf',
                    'L4uGnXg2RfTN8MRBvpi9eHesUM4MaTpMs3bu4CB1tNPhmL2Adxfe',
                    'KyTmmXBLzczKBik2rR6bs5cyNXDtJQ4mF5Y7fd37cfEkGFXyyfpx']

    transaction.sign(private_keys)

    assert str(transaction.txn) == "SegWitTransaction(version=1, ins=[TxIn(txid=b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733, txout=0, script_sig=0014fbbe46294cdc9c856ebb67fb635bbdfe42fc9950, sequence=4294967295, witness=Witness([\"3044022078b8f3b2333b31a2eb97f68c95d5a6676630f7ba984484ad735151bb95ed233d0220568167c221bc811c1f9059256510b8490b21e12d0970fb79275066b3b7b7f1ea01\", \"02e9f99190d0b977beb0699252b1ed292857d37a45c9ca4999945946b031b0eb67\"])), TxIn(txid=b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733, txout=0, script_sig=00142ad96ecfe31db2db7a4c2375806e1bb5d0ccbc3c, sequence=4294967295, witness=Witness([\"3045022100f493e4e5a84461bb86001d922a03fede43663d785c731b969a7d802fe75b58800220446a80fcf06b98b8af0e8e37a8216cea7261a22b755461f819f81b3e59bdbae601\", \"02e0730b8440866d668572a70aa7b96f7578485ae5c2538aeba3d1a06a20ea10e0\"])), TxIn(txid=b4fec0df077fbb40f95bd5eeb6762374da77418bc5c8ca8a20d383e2cca32733, txout=0, script_sig=00144ad55522152767cec4e49861ac3e3d5130eb1b3f, sequence=4294967295, witness=Witness([\"30440220372e0b783cb23fbe9cfe88f4ac3fd24d6c0c46605907344d3c98eae846148583022008877434be7192756a5f2da2daca5d5ce357dcedb73a9d1ab273d19874d2758d01\", \"0212d1626dfbdf83c66fb033ccc60cc99b3320fa176a726df204172b908e6824e6\"]))], outs=[TxOut(value=102, n=0, scriptPubKey='OP_HASH160 35bdc692c8ff698a482a5bec793ab28bd475dd8c OP_EQUAL'), TxOut(value=21533, n=1, scriptPubKey='OP_HASH160 7671ff0719b289944ce871df51b6d5fe4ab02a7f OP_EQUAL'), TxOut(value=36297, n=2, scriptPubKey='OP_HASH160 322cff52ece9716c1e4464bef9e8f2fea14b524d OP_EQUAL')], locktime=Locktime(0))"
    assert transaction.is_signed
