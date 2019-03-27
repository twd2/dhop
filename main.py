#!/usr/bin/env python3

import os
import os.path
import random
import sys
import time

import allocator
import opseq
import server
from spec.naive import NaiveAllocator
import trace


def main():
  result_dir = 'results'
  try:
    os.makedirs(result_dir)
  except FileExistsError:
    pass
  if len(sys.argv) < 2:
    print('Usage: main.py filename arguments...')
    return
  print('[INFO] Start')
  forkd = server.ForkServer(sys.argv[1:])
  forkd.wait_for_ready()
  last_time = time.time()
  begin_time = time.time()
  eps = 0
  total = 0
  crashes = 0
  min_loss = 0xffffffff
  while True:
    child_info = forkd.fork()
    ator = NaiveAllocator()
    ator.attach(*child_info)
    try:
      ator.init()
      ops = opseq.rand(random.randint(0, 20))
      ator.execute(ops)
    except allocator.ExitingError as e:
      crashes += 1
    ator.kill()
    ator.wait()
    loss = ator.loss()
    if loss < min_loss:
      min_loss = loss
    if loss == 0:
      end_time = time.time()
      print('\n[INFO] loss = 0\n[INFO] Congratulations! The desired heap layout is achieved.')
      with open(result_dir + '/trace.txt', 'w') as f:
        trace.dump_trace(f, ator.allocator_trace)
        print('[INFO] The trace is written to {}/trace.txt.'.format(result_dir))
      with open(result_dir + '/layout.txt', 'w') as f:
        trace.dump_layout(f, trace.trace_to_layout(ator.allocator_trace))
        print('[INFO] The layout is written to {}/layout.txt.'.format(result_dir))
      with open(result_dir + '/opseq.txt', 'w') as f:
        opseq.dump_ops(f, ops)
        print('[INFO] The operations sequence is written to {}/opseq.txt.'.format(result_dir))
      with open(result_dir + '/input.txt', 'wb') as f:
        f.write(b''.join(ator.input_trace))
        print('[INFO] The input is written to {}/input.txt.'.format(result_dir))
      time_usage = end_time - begin_time
      print('[INFO] {} crashes, {} totally, {:.6f} seconds, {:.2f} executions / sec'
            .format(crashes, total, time_usage, total / time_usage))
      break
    eps += 1
    total += 1
    current_time = time.time()
    if current_time - last_time >= 1.0:
      last_time = current_time
      print('\r[INFO] {} executions / sec, {} crashes, {} totally, loss = {}'
            .format(eps, crashes, total, min_loss), end='')
      eps = 0
  forkd.kill()
  forkd.wait_for_exit()
  print('[INFO] Done.')
  return 0


if __name__ == '__main__':
  #exit(asyncio.get_event_loop().run_until_complete(main()))
  exit(main())
