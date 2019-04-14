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
parser.add_argument('-o', '--output', default='results/tracer',
                    help='specify the result directory, default: results/tracer')
parser.add_argument('args', nargs='+', help='executable and its arguments')


def main():
  try:
    os.makedirs(args.output)
  except FileExistsError:
    pass
  print('[INFO] Start')
  forkd = server.ForkServer(True, args.args, args.allocator)
  forkd.hook_addr = 0x924
  forkd.init()
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
        data = ator.read_leftovers().decode()
        while True:
          try:
            sys.stdout.write(data)
            sys.stdout.flush()
            break
          except BlockingIOError:
            pass
  except allocator.ExitingError:
    pass
  print('[INFO] Exited.')
  ator.fix_output_trace()
  write_results(args.output, ator, None, "tracer's ", '', True)
  forkd.kill()
  forkd.wait_for_exit()
  print('[INFO] Done.')
  return 0


if __name__ == '__main__':
  args = parser.parse_args()
  exit(main())
