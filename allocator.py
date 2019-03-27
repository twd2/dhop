import functools
import os
import select
import signal

import opseq
from utils import *


class ExitingError(Exception):
  pass


# Base class of allocators' spec.
class AbstractAllocator():
  malloc_ops = ()
  free_ops = ()

  def __init__(self):
    self.malloc_ops = tuple(map(lambda f: functools.partial(f, self), self.malloc_ops))
    self.free_ops = tuple(map(lambda f: functools.partial(f, self), self.free_ops))

  def attach(self, pid, inspect_fd, stdin_fd, stdout_fd, epoll):
    # attach this allocator spec to an executing process
    self.pid = pid
    self.inspect_fd = inspect_fd
    self.stdin_fd = stdin_fd
    self.stdout_fd = stdout_fd
    self.epoll = epoll
    self.buff = b''
    self.allocator_trace = []
    self.full_trace = [] # TODO
    self.input_trace = []
    self.a_addr = 0x0
    self.b_addr = 0xffffffffffffffff

  def update_allocator_trace(self):
    trace = unpack_packets(read_leftovers(self.inspect_fd, is_already_nonblock=True))
    self.allocator_trace.extend(trace)
    for type, _, _, _ in trace:
      if type == TYPE_EXIT:
        #print('[WARN] target problem exited!')
        raise ExitingError()

  def init(self):
    self._init()
    self.update_allocator_trace()

  def wait(self):
    try:
      while True:
        events = self.epoll.poll()
        if (self.stdout_fd, select.EPOLLIN) in events:
          read_leftovers(self.stdout_fd, is_already_nonblock=True)
        if (self.inspect_fd, select.EPOLLIN) in events:
          self.update_allocator_trace()
    except ExitingError as e:
      pass

  def fini(self):
    self._fini()
    self.wait()

  def kill(self):
    return os.kill(self.pid, signal.SIGKILL)

  # the default rule
  def alloc_a(self, i, arg):
    self.malloc(0, 32)
    self.update_allocator_trace()
    self.a_addr = self.allocator_trace[-1][3]

  def alloc_b(self, i, arg):
    self.malloc(0, 32)
    self.update_allocator_trace()
    self.b_addr = self.allocator_trace[-1][3]

  def loss(self):
    return abs(-64 - (self.b_addr - self.a_addr))

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
    self.input_trace.append(data)
    assert(os.write(self.stdin_fd, data) == len(data))

  def malloc(self, i, size):
    return self.malloc_ops[i](size)

  def free(self, i, ref):
    return self.free_ops[i](ref)

  def do_op(self, op):
    if op.type == opseq.HeapOpType.A:
      return self.alloc_a(op.i, op.arg)
    elif op.type == opseq.HeapOpType.B:
      return self.alloc_b(op.i, op.arg)

    if op.type == opseq.HeapOpType.Alloc:
      ops = self.malloc_ops
    elif op.type == opseq.HeapOpType.Free:
      ops = self.free_ops
    else:
      assert(False)
    ret = ops[op.i % len(ops)](op.arg)
    self.update_allocator_trace()
    return ret

  def execute(self, ops):
    ref_to_arg = {}
    for ref, (type, i, arg) in enumerate(ops):
      if type == opseq.HeapOpType.Alloc:
        ref_to_arg[ref] = self.malloc_ops[i % len(self.malloc_ops)](arg)
      elif type == opseq.HeapOpType.Free:
        self.free_ops[i % len(self.free_ops)](ref_to_arg.pop(arg))
      elif type == opseq.HeapOpType.A:
        ref_a = self.alloc_a(i, arg)
      elif type == opseq.HeapOpType.B:
        ref_b = self.alloc_b(i, arg)
      else:
        assert(False)
      self.update_allocator_trace()


if __name__ == '__main__':
  from spec.naive import NaiveAllocator
  na = NaiveAllocator()
  print(na)
  print(NaiveAllocator.malloc_ops)
