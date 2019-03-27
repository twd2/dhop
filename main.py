#!/usr/bin/env python3

import copy
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


def execute_ops(forkd, ator_spec, ops):
  child_info = forkd.fork()
  ator = ator_spec()
  ator.attach(*child_info)
  ator.init()
  ator.execute(ops)
  ator.kill()
  ator.wait()
  return ator


def optimize_ops(forkd, ator_spec, ops):
  dirty = True
  while dirty:
    dirty = False
    for i, (type, _, _) in enumerate(ops):
      if type == opseq.HeapOpType.A or type == opseq.HeapOpType.B:
        continue
      # Try to remove
      new_ops = copy.deepcopy(ops)
      new_ops = opseq.remove_op(new_ops, i)
      try:
        # and check
        ator = execute_ops(forkd, ator_spec, new_ops)
        if ator.loss() == 0:
          # If loss is still zero, this op can be removed.
          dirty = True
          ops = new_ops
          break
      except allocator.ExitingError as e:
        pass
  ator = execute_ops(forkd, ator_spec, ops)
  return ator, ops


def write_results(result_dir, ator, ops, adj='', prefix=''):
  with open('{}/{}trace.txt'.format(result_dir, prefix), 'w') as f:
    trace.dump_trace(f, ator.allocator_trace)
    print('[INFO] The {}trace is written to {}/{}trace.txt.'.format(adj, result_dir, prefix))
  with open('{}/{}layout.txt'.format(result_dir, prefix), 'w') as f:
    trace.dump_layout(f, trace.trace_to_layout(ator.allocator_trace), ator.a_addr, ator.b_addr)
    print('[INFO] The {}layout is written to {}/{}layout.txt.'.format(adj, result_dir, prefix))
  with open('{}/{}opseq.txt'.format(result_dir, prefix), 'w') as f:
    opseq.dump_ops(f, ops)
    print('[INFO] The {}operations sequence is written to {}/{}opseq.txt.'.format(adj, result_dir, prefix))
  with open('{}/{}input.txt'.format(result_dir, prefix), 'wb') as f:
    f.write(b''.join(ator.input_trace))
    print('[INFO] The {}input is written to {}/{}input.txt.'.format(adj, result_dir, prefix))


def main():
  # TODO: parameterize
  result_dir = 'results'
  ator_spec = NaiveAllocator
  optimize = True
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
  min_loss = 0xffffffffffffffff
  while True:
    ops = opseq.rand(random.randint(0, 20))
    ator = None
    try:
      ator = execute_ops(forkd, ator_spec, ops)
    except allocator.ExitingError as e:
      crashes += 1
    if ator:
      loss = ator.loss()
      if loss == 0:
        end_time = time.time()
        print('\n[INFO] loss = 0\n[INFO] Congratulations! The desired heap layout is achieved.')
        write_results(result_dir, ator, ops)
        if optimize:
          print('[INFO] Optimizing results... ', end='')
          ator, ops = optimize_ops(forkd, ator_spec, ops)
          print('done!')
          write_results(result_dir, ator, ops, 'optimized ', 'opt_')
        time_usage = end_time - begin_time
        print('[INFO] {} crashes, {} totally, {:.6f} seconds, {:.2f} executions / sec'
              .format(crashes, total, time_usage, total / time_usage))
        break
      if loss < min_loss:
        min_loss = loss
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
