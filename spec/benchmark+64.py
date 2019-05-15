import allocator


# This is the spec of `benchmark.c`.
class Allocator(allocator.AbstractAllocator):
  def __init__(self):
    super().__init__()

  def loss(self):
    return abs(+64 - (self.b_addr - self.a_addr))

  def _init(self):
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
