from dataclasses import dataclass

@dataclass
class UTXOData:
    txid: str
    output_num: int
    address: str
    script: str
    value: int
    confirmations: int

    def is_confirmed(self):
        return self.confirmations > 0

    def standard_format(self):
        """ returns data in standard format as shown in blockchain.py """
        return [self.txid, self.output_num, self.address, self.script, self.value, self.confirmations]
