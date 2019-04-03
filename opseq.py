import collections
import enum
import random

from utils import *


# Generate and modify heap op sequences, keeping the constraints.


HeapOp = collections.namedtuple('HeapOp', ['type', 'i', 'arg'])
HeapOpType = enum.Enum('HeapOpType', ('Alloc', 'Free', 'A', 'B'))


def rand_i():
  return random.randint(0, 1 << 20)


def rand_size():
  if random.randint(0, 1):
    return random.choice([16, 32, 64, 128, 256, 512, 1024, 4096, 1 << 20, 2 << 20, 4 << 20, 8 << 20])
  else:
    return random.randint(1, 1024) * 16


def rand(length, malloc_ratio=0.5):
  ref_set = set()
  ops = []
  a_index = random.randint(0, length)
  for i in range(length + 1):
    if i == a_index:
      ops.append(HeapOp(HeapOpType.A, rand_i(), rand_size()))
    else:
      type = random.choices([HeapOpType.Alloc, HeapOpType.Free],
                            [malloc_ratio, 1.0 - malloc_ratio])[0]
      if type == HeapOpType.Alloc or not ref_set:
        ref_set.add(i)
        ops.append(HeapOp(HeapOpType.Alloc, rand_i(), rand_size()))
      elif type == HeapOpType.Free:
        to_be_free = random.choice(list(ref_set))
        ref_set.remove(to_be_free)
        ops.append(HeapOp(HeapOpType.Free, rand_i(), to_be_free))
      else:
        assert(False)
  ops.append(HeapOp(HeapOpType.B, rand_i(), rand_size()))
  return ops


def __insert_adjust(ops, pos):
  for i in range(pos, len(ops)):
    if ops[i].type == HeapOpType.Free and ops[i].arg >= pos:
      ops[i] = HeapOp(ops[i].type, ops[i].i, ops[i].arg + 1)
  return ops


def insert_malloc(ops, pos, i=None, size=None):
  ops = __insert_adjust(ops, pos)
  if i == None:
    i = rand_i()
  if size == None:
    size = rand_size()
  ops.insert(pos, HeapOp(HeapOpType.Alloc, i, size))
  return ops


def insert_free(ops, pos, i=None, ref=None):
  ref_set = set()
  for i in range(pos):
    if ops[i].type == HeapOpType.Alloc:
      ref_set.add(i)
    elif ops[i].type == HeapOpType.Free:
      ref_set.remove(ops[i].arg)
    elif ops[i].type == HeapOpType.A or ops[i].type == HeapOpType.B:
      pass
    else:
      assert(False)
  if not ref_set:  # nothing can be free
    return ops
  if i == None:
    i = rand_i()
  if ref == None:
    ref = random.choice(list(ref_set))
  ops = remove_free_by_ref(ops, ref)  # remove previous free op
  ops = __insert_adjust(ops, pos)
  ops.insert(pos, HeapOp(HeapOpType.Free, i, ref))
  return ops


def __remove_adjust(ops, pos):
  for i in range(pos, len(ops)):
    if ops[i].type == HeapOpType.Free and ops[i].arg >= pos:
      ops[i] = HeapOp(ops[i].type, ops[i].i, ops[i].arg - 1)
  return ops


def remove_free_by_ref(ops, ref):
  pair_free = None
  # TODO: optimize
  for i, (type, _, arg) in enumerate(ops):
    if type == HeapOpType.Free and arg == ref:
      pair_free = i
      break
  if pair_free != None:
    ops = remove_op(ops, pair_free)
  return ops


def remove_op(ops, pos):
  if ops[pos].type == HeapOpType.A or ops[pos].type == HeapOpType.B:
    assert(False)
  if ops[pos].type == HeapOpType.Alloc:
    # find and remove corresponding free, if exists
    ops = remove_free_by_ref(ops, pos)
  ops = __remove_adjust(ops, pos)
  del ops[pos]
  return ops


def mutate_malloc(ops, pos):
  assert(ops[pos].type == HeapOpType.Alloc or ops[pos].type == HeapOpType.A or ops[pos].type == HeapOpType.B)
  new_i = rand_i()
  t = random.randint(0, 2)
  if t == 0:
    new_size = max(ops[pos].arg - 16, 16)
  elif t == 1:
    new_size = min(ops[pos].arg + 16, 1 << 32)
  elif t == 2:
    new_size = rand_size()
  else:
    assert(False)
  ops[pos] = HeapOp(ops[pos].type, rand_i(), new_size)
  return ops


def mutate(ops):
  t = random.randint(0, 3 if len(ops) > 2 else 2)
  if t == 0:
    pos = random.randint(0, len(ops))
    ops = insert_malloc(ops, pos)
  elif t == 1:
    pos = random.randint(0, len(ops))
    ops = insert_free(ops, pos)
  elif t == 2:
    pos = random.randint(0, len(ops) - 1)
    if ops[pos].type == HeapOpType.A or ops[pos].type == HeapOpType.B:
      ops = mutate_malloc(ops, pos)
    else:
      ops = remove_op(ops, pos)
  elif t == 3:
    pos = random.randint(0, len(ops) - 1)
    while ops[pos].type != HeapOpType.Alloc:
      pos = random.randint(0, len(ops) - 1)
    ops = mutate_malloc(ops, pos)
  else:
    assert(False)
  return ops


def dump_ops(fo, ops):
  count = 0
  for ref, (type, i, arg) in enumerate(ops):
    fo.write('// {} allocated chunks\n'.format(count))
    if type == HeapOpType.Alloc:
      fo.write('ptr{} = malloc{}({});\n'.format(ref, i, arg))
      count += 1
    elif type == HeapOpType.Free:
      fo.write('free{}(ptr{});\n'.format(i, arg))
      count -= 1
    elif type == HeapOpType.A:
      fo.write('ptrA = malloc{}({});\n'.format(i, arg))
    elif type == HeapOpType.B:
      fo.write('ptrB = malloc{}({});\n'.format(i, arg))
    else:
      assert(False)
  fo.write('// {} allocated chunks\n'.format(count))


if __name__ == '__main__':
  ops = rand(20, 0.5)
  with open('results/before.c', 'w') as f:
    dump_ops(f, ops)
  mutate(ops)
  with open('results/after.c', 'w') as f:
    dump_ops(f, ops)
