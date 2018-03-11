import requests
import time


class BitcoinPrice:

    def __init__(self, currency='USD', source='coinmarketcap'):

        self.source = source
        self.last_request = 0  # unix timestamp of last price request
        self.last_price = 0  # last requested price

        self.valid_sources = {
            'coinmarketcap': self.coinmarketcap(currency),
            'blockchaininfo': self.blockchaininfo(currency),
            'gdax': self.gdax(currency),
            'bitstamp': self.bitstamp(currency),
        }

    def fetch_price(self):
        # Leaves 60 seconds between price requests
        if time.time() - self.last_request >= 60:
            if self.source not in self.valid_sources:
                raise Exception(f'{self.source} is not a valid source!')
            else:
                self.last_price = self.valid_sources[self.source]
                self.last_request = time.time()
                return self.last_price

    @staticmethod
    def coinmarketcap(currency):
        valid_currencies = ["AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK",
                            "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS",
                            "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD",
                            "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB",
                            "TRY", "TWD", "ZAR", "USD"]

        # Currency defaults to USD
        if currency not in valid_currencies:
            print(f'{currency} is not a valid currency! Defaulting to USD...')
            currency = 'USD'

        url = 'https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert='
        data = requests.get(url + currency).json()[0]
        # will return the currency ticker as well for all methods, because of
        # the ability to default to USD silently-ish
        return data[f'price_{currency.lower()}'], currency.upper()

    @staticmethod
    def blockchaininfo(currency):
        valid_currencies = ['USD', 'AUD', 'BRL', 'CAD', 'CHF', 'CLP', 'CNY',
                            'DKK', 'EUR', 'GBP', 'HKD', 'INR', 'ISK', 'JPY',
                            'KRW', 'NZD', 'PLN', 'RUB', 'SEK', 'SGD', 'THB',
                            'TWD']

        # Currency defaults to USD
        if currency not in valid_currencies:
            print(f'{currency} is not a valid currency! Defaulting to USD...')
            currency = 'USD'

        url = 'https://blockchain.info/ticker'
        data = requests.get(url).json()
        return data[currency.upper()]['last'], currency.upper()

    @staticmethod
    def gdax(currency):
        valid_currencies = ["EUR", "USD", "GBP"]

        # Currency defaults to USD
        if currency not in valid_currencies:
            print(f'{currency} is not a valid currency! Defaulting to USD...')
            currency = 'USD'

        url = f'https://api.gdax.com/products/BTC-{currency}/ticker'
        data = requests.get(url).json()
        return data['price'], currency.upper()

    @staticmethod
    def bitstamp(currency):
        valid_currencies = ["EUR", "USD"]

        # Currency defaults to USD
        if currency not in valid_currencies:
            print(f'{currency} is not a valid currency! Defaulting to USD...')
            currency = 'USD'

        url = f'https://www.bitstamp.net/api/v2/ticker/btc{currency}/'
        data = requests.get(url).json()
        return data['last'], currency.upper()
