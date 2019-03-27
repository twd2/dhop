import os

from utils import *


def trace_to_layout(trace):
  regions = {}
  #TODO


def dump_layout(fo, layout):
  pass


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
