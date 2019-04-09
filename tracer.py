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
import utils

from solver import write_results


parser = argparse.ArgumentParser()
parser.add_argument('-a', '--allocator', help='specify the allocator library (.so)')
parser.add_argument('-o', '--output', default='results', help='specify the result directory')
parser.add_argument('args', nargs='+', help='executable and its arguments')


def main():
  try:
    os.makedirs(args.output)
  except FileExistsError:
    pass
  if len(sys.argv) < 2:
    print('Usage: {} filename arguments...'.format(args.args))
    return
  print('[INFO] Start')
  forkd = server.ForkServer(args.args, args.allocator)
  forkd.wait_for_ready()
  child_info = forkd.fork()
  ator = allocator.AbstractAllocator()
  ator.record_full_trace = True
  ator.attach(*child_info)
  epoll = select.epoll(2)
  utils.set_nonblock(sys.stdin.fileno(), True)
  epoll.register(sys.stdin.fileno(), select.EPOLLIN)
  epoll.register(forkd.epoll.fileno(), select.EPOLLIN)
  try:
    while True:
      events = epoll.poll()
      if (sys.stdin.fileno(), select.EPOLLIN) in events:
        ator.write(utils.read_leftovers(sys.stdin.fileno(), is_already_nonblock=True))
      if (forkd.epoll.fileno(), select.EPOLLIN) in events:
        sys.stdout.write(ator.read_leftovers().decode())
        sys.stdout.flush()
  except allocator.ExitingError:
    pass
  print('[INFO] Exited.')
  write_results(args.output, ator, None, "tracer's ", 'tracer_', True)
  forkd.kill()
  forkd.wait_for_exit()
  print('[INFO] Done.')
  return 0


if __name__ == '__main__':
  args = parser.parse_args()
  exit(main())
