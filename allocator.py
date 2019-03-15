import functools
import os

import opseq
from utils import *

# Base class of allocators' spec.

class AbstractAllocator():
  malloc_ops = ()
  free_ops = ()

  def __init__(self):
    self.malloc_ops = tuple(map(lambda f: functools.partial(f, self), self.malloc_ops))
    self.free_ops = tuple(map(lambda f: functools.partial(f, self), self.free_ops))
    self.inspect_fd = 3
    self.stdin_fd = 1  # ???
    self.stdout_fd = 0  # ???
    self.buff = b''
    self.allocator_trace = []
    self.full_trace = [] # TODO

  def attach(self, inspect_fd, stdin_fd, stdout_fd):
    # attach this allocator spec to an executing process
    self.inspect_fd = inspect_fd
    self.stdin_fd = stdin_fd
    self.stdout_fd = stdout_fd

  def update_allocator_trace(self):
    self.allocator_trace.extend(unpack_packets(read_leftovers(self.inspect_fd)))

  def init(self):
    self._init()
    self.update_allocator_trace()

  def read_until(self, u):
    pos = self.buff.find(u)
    while pos < 0:
      chunk = os.read(self.stdout_fd, 4096)
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
      chunk = os.read(self.stdout_fd, remaining)
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
