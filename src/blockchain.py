import requests


class AddressData:

    def __init__(self, addresses):
        # Addresses should be passed as a list
        self.addresses = addresses
        self.raw_data = {}
        # balance of all addresses
        self.wallet_balance = self.raw_data['wallet']['final_balance']

    def _get_api_data(self):

        url = f'https://blockchain.info/multiaddr?active='
        for a in self.addresses:
            url += self.addresses[self.addresses.index(a)] + '|'
        data = requests.get(url).json()
        self.raw_data = data

    def _get_address_data(self, address):
        """ Returns *specific* address data """
        pass

    def get_address_balance(self, address):
        """ Returns balance in satoshis """
        if address in self.addresses:
            pass
        else:
            raise ValueError('Address not in self.addresses')


if __name__ == '__main__':

    ad = AddressData(['37uP4pDfbbgBh6WAkmMeA4KNjyqUY5L544',
                     '32Q3Eb6NxrShRAUCzAd3wARVvRm5M9o5F5'])
