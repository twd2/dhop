#!/usr/bin/env python3

import sys
import time

with open(sys.argv[1], 'r') as f:
  time.sleep(0.2)
  while True:
    time.sleep(0.02)
    ch = f.read(1)
    if not ch:
      break
    if ch == '\n':
      time.sleep(0.08)
    sys.stdout.write(ch)
    sys.stdout.flush()
