# DHOP: Discover Heap OPerations

## Features

* Discover inputs that trigger heap operations in a binary program.
* Find inputs to achieve the desired heap layout.

## Prerequisites

* [Python 3](https://www.python.org/downloads/)
* GCC (`sudo apt install gcc g++ make`)
* [Capstone Engine](https://github.com/aquynh/capstone) (`sudo apt install libcapstone-dev`)
* [RetDec](https://github.com/avast/retdec) or [IDA Pro](https://www.hex-rays.com/cgi-bin/quote.cgi)

## Usage

```bash
make
./tracer.py test/naive
./tracer.py -a allocator/simplemalloc/simplemalloc.so test/naive
./solver.py -s random naive test/naive
./solver.py -a allocator/simplemalloc/simplemalloc.so -s random naive test/naive
```
