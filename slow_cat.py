#!/usr/bin/env python3

import sys
import time

timing = [0.2, 0.02, 0.08]

if len(sys.argv) >= 3:
  timing = [0.5, 0.2, 0.8]

try:
  with open(sys.argv[1], 'r') as f:
    time.sleep(timing[0])
    while True:
      time.sleep(timing[1])
      ch = f.read(1)
      if not ch:
        break
      if ch == '\n':
        time.sleep(timing[2])
      sys.stdout.write(ch)
      sys.stdout.flush()
  sys.stdout.close()
except BrokenPipeError:
  pass
