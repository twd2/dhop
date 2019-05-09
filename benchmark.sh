#!/bin/bash
#allocator/simplemalloc/simplemalloc.so 
for allocator in "" #allocator/dlmalloc-2.8.6/malloc.so allocator/tcmalloc-2.7/libtcmalloc.so allocator/jemalloc-5.2.0/libjemalloc.so allocator/uClibc-ng-1.0.31/ucmalloc.so allocator/avr-libc-2.0.0/malloc.so allocator/musl-1.1.22/malloc.so
do
  for solver in random directed diversity
  do
    for ((i = 0; i < 10; i++))
    do
      echo ${allocator}-${solver}-${i}
      ./solver.py -a "${allocator}" -s ${solver} -o results/${solver}_${i}_`date +%Y%m%d%H%M%S%N` spec/naive.py test/naive
    done
  done
done
