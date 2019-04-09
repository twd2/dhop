import random

import opseq


class Solver():
  def __init__(self, *args):
    pass

  def get_candidates(self):
    return [opseq.rand(random.randint(0, 20))]

  def update_result(self, ops, ator):
    pass
