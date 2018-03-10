import requests


class Coinmarketcap:

    @staticmethod
    def bitcoin_price(currency):
        valid_currencies = ["AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK",
                            "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS",
                            "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD",
                            "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB",
                            "TRY", "TWD", "ZAR"]
        if currency.upper() in valid_currencies:
            url = 'https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert='
            data = requests.get(url + currency).json()[0]
            return data[f'price_{currency.lower()}']
        else:
            raise ValueError('Currency ticker not valid')


class Bitfinex:
    pass
