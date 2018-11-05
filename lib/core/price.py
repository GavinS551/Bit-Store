# Copyright (C) 2018  Gavin Shaughnessy
#
# Bit-Store is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import time
import functools
import json

import requests

from . import config


class BtcPriceConnectionError(Exception):
    pass


def _source_to_cls(source):
    """ returns class corresponding to config var source string (assertion below
    ensures that config keys and sources keys are in sync)
    """
    sources = {
        'coinbase': Coinbase
    }
    # make sure all sources are implemented
    assert all(s in sources for s in config.POSSIBLE_PRICE_API_SOURCES)

    if source.lower() not in sources:
        raise NotImplementedError(f'{source} is an invalid source')

    return sources[source]


def source_valid_currencies(source):
    """ returns supported currencies for passed source """
    return _source_to_cls(source).currencies


def price_api(source, currency, refresh_rate, timeout=10):
    source_cls = _source_to_cls(source)
    return source_cls(currency, refresh_rate, timeout)


class _BitcoinPriceBaseClass:
    """ Sub-classes should implement price property that returns current
    price of 1 BTC in self.currency units.

    All connection errors should be re-raised as BtcPriceConnectionError
    """

    # should be overridden by subclasses
    # list that contains all currencies that interface supports
    currencies = []

    def __init__(self, currency, refresh_rate, timeout):
        self.currency = currency
        self.refresh_rate = refresh_rate
        self.timeout = timeout

        if self.currency not in self.currencies:
            raise NotImplementedError(f'"{self.currency}" is not an implemented currency for this interface')

    def limit_requests(func):
        """ limit func calls to once every self.refresh_rate seconds,
        returns cached data if call is made more often than that
        """
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # initialise cache values
            if not hasattr(self, 'last_request_time'):
                self.last_request_time = 0
            if not hasattr(self, 'cached_price_data'):
                self.cached_price_data = None

            if time.time() - self.last_request_time > self.refresh_rate:
                data = func(self, *args, **kwargs)

                self.last_request_time = time.time()
                self.cached_price_data = data

                return data
            else:
                return self.cached_price_data

        return wrapper

    @property
    def price(self):
        raise NotImplementedError


class Coinbase(_BitcoinPriceBaseClass):

    currencies = ['AED', 'AFN', 'ALL', 'AMD', 'ANG', 'AOA', 'ARS', 'AUD', 'AWG', 'AZN', 'BAM',
                  'BBD', 'BDT', 'BGN', 'BHD', 'BIF', 'BMD', 'BND', 'BOB', 'BRL', 'BSD', 'BTN',
                  'BWP', 'BYN', 'BYR', 'BZD', 'CAD', 'CDF', 'CHF', 'CLF', 'CLP', 'CNH', 'CNY',
                  'COP', 'CRC', 'CUC', 'CVE', 'CZK', 'DJF', 'DKK', 'DOP', 'DZD', 'EEK', 'EGP',
                  'ERN', 'ETB', 'EUR', 'FJD', 'FKP', 'GBP', 'GEL', 'GGP', 'GHS', 'GIP', 'GMD',
                  'GNF', 'GTQ', 'GYD', 'HKD', 'HNL', 'HRK', 'HTG', 'HUF', 'IDR', 'ILS', 'IMP',
                  'INR', 'IQD', 'ISK', 'JEP', 'JMD', 'JOD', 'JPY', 'KES', 'KGS', 'KHR', 'KMF',
                  'KRW', 'KWD', 'KYD', 'KZT', 'LAK', 'LBP', 'LKR', 'LRD', 'LSL', 'LTL', 'LVL',
                  'LYD', 'MAD', 'MDL', 'MGA', 'MKD', 'MMK', 'MNT', 'MOP', 'MRO', 'MTL', 'MUR',
                  'MVR', 'MWK', 'MXN', 'MYR', 'MZN', 'NAD', 'NGN', 'NIO', 'NOK', 'NPR', 'NZD',
                  'OMR', 'PAB', 'PEN', 'PGK', 'PHP', 'PKR', 'PLN', 'PYG', 'QAR', 'RON', 'RSD',
                  'RUB', 'RWF', 'SAR', 'SBD', 'SCR', 'SEK', 'SGD', 'SHP', 'SLL', 'SOS', 'SRD',
                  'SSP', 'STD', 'SVC', 'SZL', 'THB', 'TJS', 'TMT', 'TND', 'TOP', 'TRY', 'TTD',
                  'TWD', 'TZS', 'UAH', 'UGX', 'USD', 'UYU', 'UZS', 'VEF', 'VND', 'VUV', 'WST',
                  'XAF', 'XAG', 'XAU', 'XCD', 'XDR', 'XOF', 'XPD', 'XPF', 'XPT', 'YER', 'ZAR',
                  'ZMK', 'ZMW', 'ZWL']

    @property
    @_BitcoinPriceBaseClass.limit_requests
    def price(self):
        url = f'https://api.coinbase.com/v2/prices/BTC-{self.currency}/spot'

        try:
            request = requests.get(url, timeout=self.timeout)
            request.raise_for_status()
            data = request.json()

        except (requests.RequestException, json.JSONDecodeError) as ex:
            raise BtcPriceConnectionError from ex

        price = float(data['data']['amount'])
        return price
