#!/bin/bash

for allocator in allocator/simplemalloc/simplemalloc.so
do
  for solver in random directed diversity
  do
    for ((i = 0; i < 10; i++))
    do
      echo ${allocator}-${solver}-${i}
      ./solver.py -a "${allocator}" -s ${solver} -o results/${solver}_${i}_`date +%Y%m%d%H%M%S%N` naive test/naive
    done
  done
done
