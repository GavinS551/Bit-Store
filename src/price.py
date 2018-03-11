import requests


class BitcoinPrice:

    def __init__(self):
        pass

    def coinmarketcap(self, currency):
        valid_currencies = ["AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK",
                            "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS",
                            "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD",
                            "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB",
                            "TRY", "TWD", "ZAR", "USD"]
        if currency.upper() in valid_currencies:
            url = 'https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert='
            data = requests.get(url + currency).json()[0]
            return data[f'price_{currency.lower()}']
        else:
            raise ValueError('Currency ticker not valid')

    def blockchaininfo(self, currency):
        valid_currencies = ['USD', 'AUD', 'BRL', 'CAD', 'CHF', 'CLP', 'CNY',
                            'DKK', 'EUR', 'GBP', 'HKD', 'INR', 'ISK', 'JPY',
                            'KRW', 'NZD', 'PLN', 'RUB', 'SEK', 'SGD', 'THB',
                            'TWD']
        if currency.upper() in valid_currencies:
            url = 'https://blockchain.info/ticker'
            data = requests.get(url).json()
            return data[currency.upper()]['last']
        else:
            raise ValueError('Currency ticker not valid')

    def gdax(self, currency):
        valid_currencies = ["EUR", "USD", "GBP"]
        if currency.upper() in valid_currencies:
            url = f'https://api.gdax.com/products/BTC-{currency}/ticker'
            data = requests.get(url).json()
            return data['price']
        else:
            raise ValueError('Currency ticker not valid')

    def bitstamp(self, currency):
        valid_currencies = ["EUR", "USD"]
        if currency.upper() in valid_currencies:
            url = f'https://www.bitstamp.net/api/v2/ticker/btc{currency}/'
            data = requests.get(url).json()
            return data['last']
        else:
            raise ValueError('Currency ticker not valid')




