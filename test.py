import pytest

from lib.core import config


if __name__ == '__main__':
    config.init()
    pytest.main(['-x', 'tests'])
