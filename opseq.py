import random

# Generate and modify heap op sequences, keeping the constraints.

TYPE_MALLOC   = 2
TYPE_FREE     = 5


def rand_size():
  if random.randint(0, 1):
    return random.choice([32, 64, 128, 256, 512, 4096, 1 << 20, 2 << 20, 4 << 20, 8 << 20])
  else:
    return random.randint(2, 1024) * 16


def rand(length, malloc_ratio=0.5):
  ref_set = set()
  ops = []
  for i in range(length):
    type = random.choices([TYPE_MALLOC, TYPE_FREE],
                          [malloc_ratio, 1.0 - malloc_ratio])[0]
    if type == TYPE_MALLOC or not ref_set:
      ref_set.add(i)
      ops.append((TYPE_MALLOC, rand_size()))
    elif type == TYPE_FREE:
      to_be_free = random.choice(list(ref_set))
      ref_set.remove(to_be_free)
      ops.append((TYPE_FREE, to_be_free))
    else:
      assert(False)
  return ops


def __insert_adjust(ops, pos):
  for i in range(pos, len(ops)):
    if ops[i][0] == TYPE_FREE and ops[i][1] >= pos:
      ops[i] = (ops[i][0], ops[i][1] + 1)
  return ops


def insert_malloc(ops, pos, size=None):
  ops = __insert_adjust(ops, pos)
  if size == None:
    size = rand_size()
  ops.insert(pos, (TYPE_MALLOC, size))
  return ops


def insert_free(ops, pos, ref=None):
  ref_set = set()
  for i in range(pos):
    if ops[i][0] == TYPE_MALLOC:
      ref_set.add(i)
    elif ops[i][0] == TYPE_FREE:
      ref_set.remove(ops[i][1])
  print(ref_set)
  if not ref_set:  # nothing can be free
    return ops
  if ref == None:
    ref = random.choice(list(ref_set))
  ops = remove_free_by_ref(ops, ref)  # remove previous free op
  ops = __insert_adjust(ops, pos)
  ops.insert(pos, (TYPE_FREE, ref))
  return ops


def __remove_adjust(ops, pos):
  for i in range(pos, len(ops)):
    if ops[i][0] == TYPE_FREE and ops[i][1] >= pos:
      ops[i] = (ops[i][0], ops[i][1] - 1)
  return ops


def remove_free_by_ref(ops, ref):
  pair_free = None
  for i, op in enumerate(ops):
    if op[0] == TYPE_FREE and op[1] == ref:
      pair_free = i
      break
  if pair_free != None:
    ops = remove_op(ops, pair_free)
  return ops


def remove_op(ops, pos):
  if ops[pos][0] == TYPE_MALLOC:
    # find and remove corresponding free, if exists
    ops = remove_free_by_ref(ops, pos)
  ops = __remove_adjust(ops, pos)
  del ops[pos]
  return ops


def print_ops(ops):
  count = 0
  for i, op in enumerate(ops):
    print('// {} allocated chunks'.format(count))
    if op[0] == TYPE_MALLOC:
      print('ptr{} = malloc({});'.format(i, op[1]))
      count += 1
    elif op[0] == TYPE_FREE:
      print('free(ptr{});'.format(op[1]))
      count -= 1
  print('// {} allocated chunks'.format(count))


if __name__ == '__main__':
  ops = rand(20, 0.5)
  print_ops(ops)
  print('------')
  #insert_malloc(ops, 10, 777)
  #remove_op(ops, 2)
  #insert_free(ops, 10)
  insert_free(ops, 10)
  print_ops(ops)
