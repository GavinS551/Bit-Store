# Bit-Store

A simple and lightweight bitcoin wallet, written in python 3.7. The gui is implemented using
python's tkinter library.

## Getting Started

Download and extract the zip file containing the program.

### Prerequisites

The program is only guaranteed to be compatible with Windows (Tested on Windows 10). Python >= 3.7 or is required.

### Installing

Use pip to install all dependencies, by using the following command in the root directory of the program:

```
pip install -r requirements.txt
```

Then the program can be started by running the main.py file in the root of the directory.

```
python main.py
```

And a tkinter gui window should be displayed.

## Running Tests

To run all tests defined in the tests directory, use the following command in the root of the directory:

```
python test.py
```

## Built With

* [base58](https://pypi.org/project/base58/) - used to verify base58check encoded bitcoin addresses
* [bitstring](https://pypi.org/project/bitstring/) - allows for easy bit manipulation required for generating bip39 mnemonics
* [btcpy](https://pypi.org/project/chainside-btcpy/) - used for creating and signing bitcoin transactions
* [cryptography](https://pypi.org/project/cryptography/) - used to implement symmetric key file encryption
* [pillow](https://pypi.org/project/Pillow/) - displaying file formats that don't have native tkinter support
* [pytest](https://pypi.org/project/pytest/) - testing suite used
* [qrcode](https://pypi.org/project/qrcode/) - creating and displaying qrcodes in the gui
* [requests](https://pypi.org/project/requests/) - for making api calls to various bitcoin apis

## Acknowledgments

UI design inspired by the popular [electrum bitcoin wallet](https://github.com/spesmilo/electrum)
