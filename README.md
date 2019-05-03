# DHOP: Discover Heap OPerations

## Features

* Discover inputs that trigger heap operations in a binary program.
* Find inputs to achieve the desired heap layout.

## Prerequisites

* [Python 3](https://www.python.org/downloads/)
* GCC (`sudo apt install gcc g++ make`)
* [Capstone Engine](https://github.com/aquynh/capstone) (`sudo apt install libcapstone-dev`)
* cmake (`sudo apt install cmake`)
* LLVM (`sudo apt install llvm-dev`)
* zlib (`sudo apt install zlib1g-dev`)

It finds the main loop by analyzing the LLVM IR code, which is lifted from the binary.
Users can use either RetDec or McSema as the lifter, and the prerequisites are as follows, respectively.

### Prerequisites for Using RetDec

* [RetDec](https://github.com/avast/retdec)

### Prerequisites for Using McSema

* [McSema](https://github.com/trailofbits/mcsema)

..., and a disassembler required by McSema, like:

* [IDA Pro](https://www.hex-rays.com/cgi-bin/quote.cgi)

## Usage

```bash
make
./tracer.py test/naive
./tracer.py -a allocator/simplemalloc/simplemalloc.so test/naive
./solver.py -s random naive test/naive
./solver.py -a allocator/simplemalloc/simplemalloc.so -s random naive test/naive
```
