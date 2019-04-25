# Building

```bash
mkdir build
cd build
cmake -DZ3_DIR=/path/to/z3 -DCMAKE_BUILD_TYPE=Debug ..
make
```

# Running

In `build`:

```bash
./z3expr test.c.ll.noattr.mem2reg
```