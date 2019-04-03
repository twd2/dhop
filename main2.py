#!/usr/bin/env python3

import os
import os.path
import select
import sys

import allocator
import opseq
import server
import trace
import utils


def main():
  result_dir = 'results'
  try:
    os.makedirs(result_dir)
  except FileExistsError:
    pass
  if len(sys.argv) < 2:
    print('Usage: {} filename arguments...'.format(sys.argv[0]))
    return
  print('[INFO] Start')
  forkd = server.ForkServer(sys.argv[1:])
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
  with open('{}/full_trace.txt'.format(result_dir), 'w') as f:
    trace.dump_trace(f, ator.full_trace)
    print('[INFO] The full trace is written to {}/full_trace.txt.'.format(result_dir))
  trace.dump_layout(sys.stdout, trace.trace_to_layout(ator.full_trace))
  forkd.kill()
  forkd.wait_for_exit()
  print('[INFO] Done.')
  return 0


if __name__ == '__main__':
  exit(main())
