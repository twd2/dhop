#!/usr/bin/env python3

import asyncio
import sys
import struct
import signal
import time
import os
import os.path
import pty

import utils

INSPECT_FD = 3
SERVER_FD  = 4
TYPE_READY    = 0
TYPE_PID      = 1
TYPE_MALLOC   = 2
TYPE_CALLOC   = 3
TYPE_REALLOC  = 4
TYPE_FREE     = 5
TYPE_WAIT     = 6
SIZEOF_PACKET = 32

def read_packet(fd):
  buff = os.read(fd, SIZEOF_PACKET)
  return struct.unpack('<QQQQ', buff)

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
  #await asyncio.sleep(1)
  print('start')
  server_pid, inspect_fd, server_fd, \
    stdin_fd, stdout_fd = start_fork_server(sys.argv[1:])
  print('waiting for fork server... ', end='')
  sys.stdout.flush()
  type, _, _, _ = read_packet(inspect_fd)
  assert(type == TYPE_READY)
  print('ready!')
  last_time = time.time()
  count = 0
  crashes = 0
  while True:
    os.write(server_fd, b'A')
    while True:
      type, _, _, pid = read_packet(inspect_fd)
      if type == TYPE_PID:
        #print('[INFO] pid', pid)
        break
      else:
        # print('[WARN] something wrong')
        pass
    #os.kill(pid, signal.SIGKILL)
    os.write(stdin_fd, b'4\n1\n')
    while True:
      type, arg1, arg2, ret = read_packet(inspect_fd)
      if type == TYPE_MALLOC:
        pass #print('[INFO] malloc({}) = {:#x}'.format(arg1, ret))
      elif type == TYPE_CALLOC:
        print('[INFO] calloc({}) = {:#x}'.format(arg1, ret))
      elif type == TYPE_REALLOC:
        print('[INFO] realloc({:#x}, {}) = {:#x}'.format(arg1, arg2, ret))
      elif type == TYPE_FREE:
        print('[INFO] free({:#x})'.format(arg1))
      elif type == TYPE_WAIT:
        status = ret
        break
    utils.read_leftovers(inspect_fd)
    utils.read_leftovers(stdout_fd)
    #print('status', status)
    if os.WIFEXITED(status):
      #print('exit, ret = {}!'.format(os.WEXITSTATUS(status)))
      pass
    else:
      crashes += 1
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

