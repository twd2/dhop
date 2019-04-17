import datetime


class SpecGen():
  def __init__(self, name='unnamed'):
    self.name = name
    self.init_code = ''
    self.fini_code = ''
    self.malloc_ops = []
    self.free_ops = []

  def add_malloc(self, code):
    self.malloc_ops.append(code)

  def add_free(self, code):
    self.free_ops.append(code)

  def gen(self):
    if not self.init_code:
      self.init_code = '    pass\n'
    if not self.fini_code:
      self.fini_code = '    pass\n'
    parts = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts.append('import allocator\n'
                 '\n\n'
                 '# {}\n'.format(self.name) +
                 '# This spec is generated at {}.\n'.format(now_str) +
                 'class Allocator(allocator.AbstractAllocator):\n'
                 '  def __init__(self):\n'
                 '    super().__init__()\n'
                 '\n'
                 '  def _init(self):\n' + self.init_code +
                 '\n'
                 '  def _fini(self):\n' + self.fini_code +
                 '\n'
                 '  # TODO: You may rewrite the following function to define your alloc A.\n'
                 '  # def alloc_a(self, i, arg):\n'
                 '  #   See allocator.py line 76.\n'
                 '\n'
                 '  # TODO: You may rewrite the following function to define your alloc B.\n'
                 '  # def alloc_b(self, i, arg):\n'
                 '  #   See allocator.py line 81.\n'
                 '\n'
                 '  # TODO: You may rewrite the following function to define your loss function.\n'
                 '  # def loss(self):\n'
                 '  #   See allocator.py line 86.\n'
                 '\n')
    for i, code in enumerate(self.malloc_ops):
      parts.append('  def malloc{}(self, size):\n'.format(i))
      parts.append(code)
      parts.append('\n')
    for i, code in enumerate(self.free_ops):
      parts.append('  def free{}(self, ref):\n'.format(i))
      parts.append(code)
      parts.append('\n')
    parts.append('  malloc_ops = (')
    buff = ''
    for i in range(len(self.malloc_ops)):
      buff += 'malloc{}, '.format(i)
    if len(self.malloc_ops) == 1:
      buff = buff[:-1]
    else:
      buff = buff[:-2]
    parts.append(buff)
    parts.append(')\n')
    parts.append('  free_ops = (')
    buff = ''
    for i in range(len(self.free_ops)):
      buff += 'free{}, '.format(i)
    if len(self.free_ops) == 1:
      buff = buff[:-1]
    else:
      buff = buff[:-2]
    parts.append(buff)
    parts.append(')\n')
    return ''.join(parts)


if __name__ == '__main__':
  g = SpecGen('test')
  g.init_code = '    # init code\n    pass\n'
  g.fini_code = '    # fini code\n    pass\n'
  g.add_malloc('    # malloc 1 code\n    pass\n')
  g.add_malloc('    # malloc 2 code\n    pass\n')
  g.add_free('    # free 1 code\n    pass\n')
  print(g.gen(), end='')
