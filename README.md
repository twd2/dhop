# DHOP: Discover Heap OPeration

## Usage

```bash
make
./tracer.py test/naive
./tracer.py -a allocator/simplemalloc/simplemalloc.so test/naive
./solver.py -s random naive test/naive
./solver.py -a allocator/simplemalloc/simplemalloc.so -s random naive test/naive
```
