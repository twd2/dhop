import random

import opseq


class Solver():
  def __init__(self, max_length=20, *args):
    self.max_length = int(max_length)

  def get_candidates(self):
    return [opseq.rand(random.randint(0, self.max_length))]

  def update_result(self, ops, ator):
    pass
