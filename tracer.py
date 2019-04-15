#!/usr/bin/env python3

import argparse
import os
import os.path
import select
import sys

import allocator
import opseq
import server
import trace

from solver import write_results
from utils import *


parser = argparse.ArgumentParser()
parser.add_argument('-a', '--allocator', help='specify the allocator library (.so)')
parser.add_argument('-o', '--output', default='results/tracer',
                    help='specify the result directory, default: results/tracer')
parser.add_argument('args', nargs='+', help='executable and its arguments')


def my_print(data):
  data = data.decode()
  while True:
    try:
      sys.stdout.write(data)
      sys.stdout.flush()
      break
    except BlockingIOError:
      pass


def malloc_free_score(trace):
  score = 0
  for type, arg1, arg2, ret in trace:
    if type in [TYPE_MALLOC, TYPE_CALLOC, TYPE_REALLOC]:
      score += 1
    elif type in [TYPE_FREE]:
      score -= 1
    elif type in [TYPE_STDIN, TYPE_STDOUT, TYPE_MAIN_LOOP, TYPE_EXIT]:
      pass
    else:
      assert(False)
  return score


def main():
  try:
    os.makedirs(args.output)
  except FileExistsError:
    pass
  print('[INFO] Start')
  forkd = server.ForkServer(True, args.args, args.allocator)
  forkd.hook_addr = 0x924  # FIXME
  forkd.init()
  child_info = forkd.fork()
  ator = allocator.AbstractAllocator()
  ator.record_full_trace = True
  ator.attach(*child_info)
  epoll = select.epoll(2)
  set_nonblock(sys.stdin.fileno(), True)
  epoll.register(sys.stdin.fileno(), select.EPOLLIN)
  epoll.register(forkd.epoll.fileno(), select.EPOLLIN)
  print('[INFO] Start interaction.')
  try:
    while True:
      events = epoll.poll()
      if (sys.stdin.fileno(), select.EPOLLIN) in events:
        data = read_leftovers(sys.stdin.fileno(), is_already_nonblock=True)
        if not data:
          print('[DEBUG] stdin stream closed.')
        if not sys.stdin.isatty():
          my_print(data)
        ator.write(data)
      if (forkd.epoll.fileno(), select.EPOLLIN) in events:
        my_print(ator.read_leftovers())
  except allocator.ExitingError:
    pass
  print('[INFO] Exited.')
  ator.fix_output_trace()
  write_results(args.output, ator, None, "tracer's ", '', True)
  traces = trace.trace_slice(ator.full_trace)
  for t in traces:
    score = malloc_free_score(t)
    print('=========== SLICE (score={}{}) ==========='.format('+' if score >= 0 else '-', abs(score)))
    trace.dump_trace(sys.stdout, t)
    print('========================================')
  forkd.kill()
  forkd.wait_for_exit()
  print('[INFO] Done.')
  return 0


if __name__ == '__main__':
  args = parser.parse_args()
  exit(main())
