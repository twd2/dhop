import os
import signal

from utils import *


def trace_to_layout(trace):
  regions = {}
  for type, arg1, arg2, ret in trace:
    if type == TYPE_MALLOC:
      regions[ret] = arg1
    elif type == TYPE_CALLOC:
      regions[ret] = arg1 * arg2
    elif type == TYPE_REALLOC:
      del regions[arg1]
      regions[ret] = arg2
    elif type == TYPE_FREE:
      del regions[arg1]
    elif type == TYPE_EXIT:
      pass
    else:
      assert(False)
  layout = list(sorted(regions.items()))
  return layout


def dump_layout(fo, layout):
  base_addr = layout[0][0]
  for begin, size in layout:
    fo.write('[0x{:x}, 0x{:x} + {}]\n'.format(begin - base_addr, begin - base_addr, size))


def dump_trace(fo, trace):
  for type, arg1, arg2, ret in trace:
    if type == TYPE_MALLOC:
      fo.write('malloc({}) = {:#x}\n'.format(arg1, ret))
    elif type == TYPE_CALLOC:
      fo.write('calloc({}) = {:#x}\n'.format(arg1, ret))
    elif type == TYPE_REALLOC:
      fo.write('realloc({:#x}, {}) = {:#x}\n'.format(arg1, arg2, ret))
    elif type == TYPE_FREE:
      fo.write('free({:#x})\n'.format(arg1))
    elif type == TYPE_EXIT:
      if os.WIFSIGNALED(ret) and os.WTERMSIG(signal.SIGKILL):
        fo.write('process killed, code: {}\n'.format(ret))
      elif os.WIFEXITED(ret):
        fo.write('process exited, code: {}\n'.format(os.WEXITSTATUS(ret)))
      else:
        fo.write('process crashed, code: {}\n'.format(ret))
    else:
      assert(False)
