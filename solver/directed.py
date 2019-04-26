import collections
import copy
import math
import random
import sys

import opseq
import trace

from utils import *


def calc_priority(prev_priority, loss, layout):
  return min(loss, prev_priority)


class Solver():
  def __init__(self, new_seed_ratio=(10 / 11), *args):
    self.new_seed_ratio = float(new_seed_ratio)
    self.buckets = collections.defaultdict(list)
    self.min_loss = 0xffffffffffffffff
    self.seed_count = 0

  def get_candidates(self):
    if not self.buckets or random.random() <= self.new_seed_ratio:
      # Generate a brand new seed.
      self.last_seed_priority, seed = 0xffffffffffffffff, opseq.rand(random.randint(0, 20))
      candidates = [seed]
    else:
      keys = list(self.buckets.keys())
      weights = list(map(lambda k: math.exp(-k / 16), keys))
      # clog('debug', 'Seeds and their weights: {} {}', keys, weights)
      key = random.choices(keys, weights)[0]
      self.last_seed_priority, seed = random.choice(self.buckets[key])
      candidates = []
      for _ in range(10):  # TODO: power schedule
        ops = copy.deepcopy(seed)
        ops = opseq.mutate(ops)
        candidates.append(ops)
    return candidates

  def update_result(self, ops, ator):
    loss = ator.loss()
    if self.new_seed_ratio < 1.0:
      if loss == 16:
        '''if random.randint(0, 99) == 0:
          clog('debug', 'current loss = {}', loss)
          clog('debug', 'Trace:')
          trace.dump_trace(sys.stdout, ator.allocator_trace)'''
      priority = calc_priority(self.last_seed_priority, loss, None)  # TODO: layout
      if priority != loss:
        # clog('debug', 'loss={}, priority={}', loss, priority)
        pass
      if loss < self.min_loss or priority in self.buckets:
        # clog('debug', 'New seed added.')
        self.buckets[priority].append((priority, ops))
        self.seed_count += 1
      if loss < self.min_loss:
          self.min_loss = loss
