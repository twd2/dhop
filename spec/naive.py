import allocator


# This is the example spec of `naive.c`.
# You can write your own spec manually, or use
# `tracer.py` to analyze the target file and
# generate the spec automagically.
class Allocator(allocator.AbstractAllocator):
  def __init__(self):
    super().__init__()

  def _init(self):
    self.write(b'6\n')  # The prologue.
    self.read_until(b'op? ')

  def _fini(self):
    self.write(b'5\n0\n')

  def malloc1(self, size):
    self.write(b'1\n' + str(size).encode() + b'\n')
    self.read_until(b'0x')
    ref = self.read_until(b'\n')[:-1]
    self.read_until(b'op? ')
    return ref

  def free1(self, ref):
    self.write(b'4\n' + ref + b'\n')
    self.read_until(b'op? ')

  malloc_ops = (malloc1,)
  free_ops = (free1,)
