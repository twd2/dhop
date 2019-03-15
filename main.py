#!/usr/bin/env python3

import asyncio
import os
import os.path
import pty
import select
import signal
import sys
import time

from utils import *
import allocator
from spec.naive import NaiveAllocator
import trace


def start_fork_server(args):
  inspect_fd_r, inspect_fd_w = os.pipe2(0)
  server_fd_r, server_fd_w = os.pipe2(0)
  stdin_fd_r, stdin_fd_w = os.pipe2(0)
  stdout_fd_r, stdout_fd_w = os.pipe2(0)
  server_pid = os.fork()
  if not server_pid:
    # child
    if inspect_fd_w == INSPECT_FD:
      os.set_inheritable(inspect_fd_w, True)
    else:
      os.dup2(inspect_fd_w, INSPECT_FD)
      os.close(inspect_fd_w)
    if server_fd_r == SERVER_FD:
      os.set_inheritable(server_fd_r, True)
    else:
      os.dup2(server_fd_r, SERVER_FD)
      os.close(server_fd_r)
    os.dup2(stdin_fd_r, pty.STDIN_FILENO)
    if stdin_fd_r != pty.STDIN_FILENO:
      os.close(stdin_fd_r)
    os.dup2(stdout_fd_w, pty.STDOUT_FILENO)
    os.dup2(stdout_fd_w, pty.STDERR_FILENO)
    if stdout_fd_w != pty.STDOUT_FILENO and stdout_fd_w != pty.STDERR_FILENO:
      os.close(stdout_fd_w)
    os.execve(args[0], args,
              {**os.environ,
               'LD_PRELOAD': os.path.dirname(os.path.realpath(__file__)) + '/wrapper.so'})
    assert(False)
  else:
    # parent
    return server_pid, inspect_fd_r, server_fd_w, stdin_fd_w, stdout_fd_r


async def main():
  if len(sys.argv) < 2:
    print('Usage: main.py filename arguments...')
    return
  print('start')
  server_pid, inspect_fd, server_fd, \
    stdin_fd, stdout_fd = start_fork_server(sys.argv[1:])
  print('waiting for fork server... ', end='')
  sys.stdout.flush()
  # Create an epoll object for 2 fds.
  fds = [inspect_fd, stdout_fd]
  epoll = select.epoll(len(fds))
  for fd in fds:
    set_nonblock(fd, True)
    epoll.register(fd, select.EPOLLIN)
  assert(epoll.poll() == [(inspect_fd, select.EPOLLIN)])
  type, _, _, _ = read_packet(inspect_fd)
  assert(type == TYPE_READY)
  print('ready!')
  last_time = time.time()
  count = 0
  crashes = 0
  while True:
    os.write(server_fd, b'A')
    # FIXME: ugly
    while True:
      events = []
      while (inspect_fd, select.EPOLLIN) not in events:
        events = epoll.poll()
      type, _, _, pid = read_packet(inspect_fd)
      if type == TYPE_PID:
        #print('[INFO] pid', pid)
        break
      else:
        # print('[WARN] something wrong')
        pass
    #os.kill(pid, signal.SIGKILL)
    ator = NaiveAllocator()
    ator.attach(inspect_fd, stdin_fd, stdout_fd, epoll)
    try:
      ator.init()
      ator.free(0, 1)
      ator.fini()
    except allocator.ExitingError as e:
      crashes += 1
    trace.dump_trace(sys.stdout, ator.allocator_trace)
    read_leftovers(inspect_fd)
    read_leftovers(stdout_fd)
    count += 1
    current_time = time.time()
    if current_time - last_time >= 1.0:
      last_time = current_time
      print('[INFO] {} executions / sec, {} crashes'.format(count, crashes))
      count = 0
  os.kill(server_pid, signal.SIGKILL)
  os.waitpid(server_pid, 0)
  print('done')
  return 0


if __name__ == '__main__':
  exit(asyncio.get_event_loop().run_until_complete(main()))

