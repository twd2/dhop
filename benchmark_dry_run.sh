#!/bin/bash
for spec in spec/benchmark-64.py spec/benchmark+64.py spec/benchmark-48.py spec/benchmark+48.py
do
  for exe in test/bm_0noise_null test/bm_0noise_php-7.2.17 test/bm_2noise_null test/bm_2noise_php-7.2.17
  do
    for allocator in "" allocator/simplemalloc/simplemalloc.so allocator/dlmalloc-2.8.6/malloc.so allocator/tcmalloc-2.7/libtcmalloc.so allocator/jemalloc-5.2.0/libjemalloc.so allocator/uClibc-ng-1.0.31/ucmalloc.so allocator/avr-libc-2.0.0/malloc.so allocator/musl-1.1.22/malloc.so
    do
      for solver in random directed
      do
        for ((i = 0; i < 10; i++))
        do
          echo ./solver.py -a "\"${allocator}\"" -s ${solver} -o results/benchmark_`date +%Y%m%d%H%M%S%N` ${spec} ${exe}
        done
      done
    done
  done
done
