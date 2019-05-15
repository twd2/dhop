#!/bin/bash

echo Using $1 processors...
./benchmark_dry_run.sh | parallel -j $1 # --use-cpus-instead-of-cores
