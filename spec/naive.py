import allocator

# This is the spec of the `naive.c`.

class NaiveAllocator(allocator.AbstractAllocator):
  def __init__(self):
    super().__init__()

  def _init(self):
    self.read_until(b'op? ')

  def _fini(self):
    self.write(b'5\n0\n')

  def malloc1(self, size):
    self.write(b'1\n' + str(size).encode() + b'\n')
    self.read_until(b'0x')
    ref = int(self.read_until(b'\n'), 16)
    self.read_until(b'op? ')
    return ref

  def free1(self, ref):
    self.write(b'4\n' + hex(ref).encode() + b'\n')
    self.read_until(b'op? ')
    return

  malloc_ops = (malloc1,)
  free_ops = (free1,)
