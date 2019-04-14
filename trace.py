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
      if arg1:
        del regions[arg1]
      regions[ret] = arg2
    elif type == TYPE_FREE:
      if arg1:
        del regions[arg1]
    elif type in [TYPE_STDIN, TYPE_STDOUT, TYPE_MAIN_LOOP, TYPE_EXIT]:
      pass
    else:
      assert(False)
  layout = list(sorted(regions.items()))
  return layout


def dump_layout(fo, layout, a_addr=None, b_addr=None):
  if not layout:
    return
  base_addr = layout[0][0] & ~0xfff
  for begin, size in layout:
    if begin == a_addr:
      marker = 'A: '
    elif begin == b_addr:
      marker = 'B: '
    else:
      marker = '   '
    fo.write('{}[0x{:x}, 0x{:x} + {})\n'.format(marker, begin - base_addr, begin - base_addr, size))


def load_trace(fo):
  trace = []
  while True:
    packet = fo.read(SIZEOF_PACKET)
    if not packet:
      break
    trace.append(struct.unpack(STRUCT_PACKET, packet))
  return trace


def dump_trace(fo, trace):
  for type, arg1, arg2, ret in trace:
    if type == TYPE_MALLOC:
      fo.write('malloc({}) = {:#x}\n'.format(arg1, ret))
    elif type == TYPE_CALLOC:
      fo.write('calloc({}, {}) = {:#x}\n'.format(arg1, arg2, ret))
    elif type == TYPE_REALLOC:
      fo.write('realloc({:#x}, {}) = {:#x}\n'.format(arg1, arg2, ret))
    elif type == TYPE_FREE:
      fo.write('free({:#x})\n'.format(arg1))
    elif type == TYPE_STDIN:
      fo.write('read(...) = {}\n'.format(arg1))
    elif type == TYPE_STDOUT:
      fo.write('write({})\n'.format(arg1))
    elif type == TYPE_MAIN_LOOP:
      fo.write('the main loop iterates.\n')
    elif type == TYPE_EXIT:
      if os.WIFSIGNALED(ret) and os.WTERMSIG(signal.SIGKILL):
        fo.write('process killed, code: {}\n'.format(ret))
      elif os.WIFEXITED(ret):
        fo.write('process exited, code: {}\n'.format(os.WEXITSTATUS(ret)))
      else:
        fo.write('process crashed, code: {}\n'.format(ret))
    else:
      assert(False)

if __name__ == '__main__':
  import sys
  dump_trace(sys.stdout, load_trace(sys.stdin.buffer))
