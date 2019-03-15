import functools
import os
import select

import opseq
from utils import *

# Base class of allocators' spec.


class ExitingError(Exception):
  pass


class AbstractAllocator():
  malloc_ops = ()
  free_ops = ()

  def __init__(self):
    self.malloc_ops = tuple(map(lambda f: functools.partial(f, self), self.malloc_ops))
    self.free_ops = tuple(map(lambda f: functools.partial(f, self), self.free_ops))
    self.inspect_fd = 3
    self.stdin_fd = 1  # ???
    self.stdout_fd = 0  # ???
    self.epoll = None
    self.buff = b''
    self.allocator_trace = []
    self.full_trace = [] # TODO

  def attach(self, inspect_fd, stdin_fd, stdout_fd, epoll):
    # attach this allocator spec to an executing process
    self.inspect_fd = inspect_fd
    self.stdin_fd = stdin_fd
    self.stdout_fd = stdout_fd
    self.epoll = epoll

  def update_allocator_trace(self):
    trace = unpack_packets(read_leftovers(self.inspect_fd))
    self.allocator_trace.extend(trace)
    for type, _, _, _ in trace:
      if type == TYPE_EXIT:
        #print('[WARN] target problem exited!')
        raise ExitingError()

  def init(self):
    self._init()
    self.update_allocator_trace()

  def fini(self):
    self._fini()
    try:
      while True:
        events = self.epoll.poll()
        if (self.stdout_fd, select.EPOLLIN) in events:
          read_leftovers(self.stdout_fd)
        if (self.inspect_fd, select.EPOLLIN) in events:
          self.update_allocator_trace()
    except ExitingError as e:
      pass

  def _read_stdout(self, length):
    while True:
      events = self.epoll.poll()
      if (self.inspect_fd, select.EPOLLIN) in events:
        self.update_allocator_trace()
      if (self.stdout_fd, select.EPOLLIN) in events:
        break
    return os.read(self.stdout_fd, length)

  def read_until(self, u):
    pos = self.buff.find(u)
    while pos < 0:
      chunk = self._read_stdout(4096)
      if not chunk:
        return None
      self.buff += chunk
      pos = self.buff.find(u)
    data = self.buff[:pos + len(u)]
    self.buff = self.buff[pos + len(u):]
    return data

  def read(self, n):
    remaining = n
    data = b''
    while remaining:
      chunk = self._read_stdout(remaining)
      if not chunk:
        return data
      data += chunk
      remaining -= len(chunk)
    return data

  def write(self, data):
    assert(os.write(self.stdin_fd, data) == len(data))

  def malloc(self, i, size):
    return self.malloc_ops[i](size)

  def free(self, i, ref):
    return self.free_ops[i](ref)

  def execute(self, op):
    if op.type == TYPE_MALLOC:
      ops = self.malloc_ops
    elif op.type == TYPE_FREE:
      ops = self.free_ops
    else:
      assert(False)
    ret = ops[op.i % len(ops)](op.arg)
    self.update_allocator_trace()
    return ret


if __name__ == '__main__':
  from spec.naive import NaiveAllocator
  na = NaiveAllocator()
  print(na)
  print(NaiveAllocator.malloc_ops)
