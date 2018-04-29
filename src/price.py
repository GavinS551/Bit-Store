import requests
import time


class BitcoinPrice:

    # TODO: CLASS NEEDS A REFACTOR

    def __init__(self, currency='USD', source='coinmarketcap', timeout=10):

        self.valid_sources = {
            'coinmarketcap': self.coinmarketcap,
            'blockchaininfo': self.blockchaininfo,
            'gdax': self.gdax,
            'bitstamp': self.bitstamp,
        }

        self.currency = currency

        self.source = source
        if self.source not in self.valid_sources:
            raise Exception(f'{self.source} is not a valid source!')

        self.last_request = 0  # unix timestamp of last price request
        self.last_price = 0  # last requested price

        self.timeout = timeout

    @property
    def price(self):
        # Leaves 60 seconds between price requests
        if time.time() - self.last_request >= 60:
            self.last_price = self.valid_sources[self.source]()
            self.last_request = time.time()
            return self.last_price
        else:
            return self.last_price

    def coinmarketcap(self):
        currency = self.currency
        valid_currencies = ["AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK",
                            "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS",
                            "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD",
                            "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB",
                            "TRY", "TWD", "ZAR", "USD"]

        if currency.upper() not in valid_currencies:
            raise ValueError(f'"{currency}" is not a valid currency for this source')

        url = 'https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert='
        data = requests.get(url + currency, timeout=self.timeout).json()[0]
        # will return the currency ticker as well for all methods, because of
        # the ability to default to USD silently-ish
        return data[f'price_{currency.lower()}']

    def blockchaininfo(self):
        currency = self.currency
        valid_currencies = ['USD', 'AUD', 'BRL', 'CAD', 'CHF', 'CLP', 'CNY',
                            'DKK', 'EUR', 'GBP', 'HKD', 'INR', 'ISK', 'JPY',
                            'KRW', 'NZD', 'PLN', 'RUB', 'SEK', 'SGD', 'THB',
                            'TWD']

        if currency.upper() not in valid_currencies:
            raise ValueError(f'"{currency}" is not a valid currency for this source')

        url = 'https://blockchain.info/ticker'
        data = requests.get(url, timeout=self.timeout).json()
        return data[currency.upper()]['last']

    def gdax(self):
        currency = self.currency
        valid_currencies = ["EUR", "USD", "GBP"]

        if currency.upper() not in valid_currencies:
            raise ValueError(f'"{currency}" is not a valid currency for this source')

        url = f'https://api.gdax.com/products/BTC-{currency}/ticker'
        data = requests.get(url, timeout=self.timeout).json()
        return data['price']

    def bitstamp(self):
        currency = self.currency
        valid_currencies = ["EUR", "USD"]

        if currency.upper() not in valid_currencies:
            raise ValueError(f'"{currency}" is not a valid currency for this source')

        url = f'https://www.bitstamp.net/api/v2/ticker/btc{currency}/'
        data = requests.get(url, timeout=self.timeout).json()
        return data['last']
