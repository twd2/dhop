#!/usr/bin/env python3

import argparse
import collections
import os
import os.path
import re
import select
import sys

import allocator
import loop_finder
import opseq
import server
import specgen
import trace

from solver import write_results
from utils import *


parser = argparse.ArgumentParser()
parser.add_argument('-a', '--allocator', help='specify the allocator library (.so)')
parser.add_argument('-o', '--output', default='results/tracer',
                    help='specify the result directory, default: results/tracer')
parser.add_argument('-l', '--loop', default='auto',
                    help='specify the address of the main loop '
                         '(auto / off / no / ADDRESS, default: auto). '
                         'Note: the address is the address in the image (ELF file).')
tool_group = parser.add_mutually_exclusive_group()
tool_group.add_argument('--ida',
                        help='specify the path of IDA Pro if you want to use IDA Pro '
                             'to find the main loop (default: empty)')
tool_group.add_argument('--retdec', default='/opt/retdec',
                        help='specify the path of RetDec if you want to use RetDec '
                             'to find the main loop (default: /opt/retdec)')
parser.add_argument('args', nargs='+', help='executable and its arguments')


def my_print(data):
  data = data.decode()
  # FIXME: ugly
  while True:
    try:
      sys.stdout.write(data)
      sys.stdout.flush()
      break
    except BlockingIOError:
      pass


def _malloc_free_score(trace):
  score = 0
  for type, arg1, arg2, ret in trace:
    if type in [TYPE_MALLOC, TYPE_CALLOC]:
      score += 1
    elif type in [TYPE_FREE]:
      score -= 1
    elif type in [TYPE_REALLOC]:
      score += -1 + 1
    elif type in [TYPE_STDIN, TYPE_STDOUT, TYPE_MAIN_LOOP, TYPE_EXIT]:
      pass
    else:
      assert(False)
  return score


def _size_in_trace(size, trace):
  for type, arg1, arg2, ret in trace:
    if type == TYPE_MALLOC and size == arg1:
      return True
    elif type == TYPE_CALLOC and size == arg1 * arg2:
      return True
    elif type == TYPE_REALLOC and size == arg2:
      return True
  return False


REF_KEYWORDS = ['id', 'ref', 'ptr', 'index', 'key']
SIZE_KEYWORDS = ['size', 'length', 'count']
BUFFER_KEYWORDS = ['name', 'content', 'data']
REF_RE = re.compile(br'^([^\d]*)((0x[\da-fA-F]+)|(\d+))([\d\D]*)$', re.MULTILINE)


def slices_to_spec(slices, read_prompt_after=True):
  # FIXME: This function is ugly, needs to be rewritten.
  executable = os.path.realpath(args.args[0])
  gen = specgen.SpecGen('This is a spec for {}.'.format(executable))

  # Init slice.
  init_stdout = b''
  for type, arg1, arg2, ret in slices[0]:
    if type == TYPE_STDOUT:
      init_stdout += arg1
  if init_stdout:
    gen.init_code = '    self.read_until({})\n'.format(repr(get_postfix(init_stdout)))
  else:
    gen.init_code = ''

  # Loop slices.
  choice_prompts = collections.defaultdict(int)
  for slice in slices[1:]:
    for type, arg1, arg2, ret in slice:
      if type == TYPE_STDOUT:
        choice_prompts[arg1] += 1
        break
  if choice_prompts:
    # TODO: this approach is naive
    choice_prompt, _ = max(choice_prompts.items(), key=lambda t: t[1])
  else:
    choice_prompt = b''
  clog('info', 'The choice prompt is {}.', repr(choice_prompt.decode()))
  if read_prompt_after and choice_prompt:
    gen.init_code += '    self.read_until({})\n'.format(repr(get_postfix(choice_prompt)))

  for slice in slices[1:]:
    clog('info', 'Processing the following slice:')
    score = _malloc_free_score(slice)
    print('~~~~~~~~~~ SLICE (score = {}{}) ~~~~~~~~~~' \
          .format('+' if score >= 0 else '-', abs(score)))
    trace.dump_trace(sys.stdout, slice)
    print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

    stdio_slice = trace.trace_slice(slice, filter=lambda ty: ty in [TYPE_STDIN, TYPE_STDOUT])[0]
    stdio_trace_by_type = collections.defaultdict(list)
    for t in stdio_slice:
      stdio_trace_by_type[t[0]].append(t)
    choice_str = stdio_trace_by_type[TYPE_STDIN][0][1]
    clog('info', 'The input to trigger this choice is {}.', repr(choice_str.decode()))

    if read_prompt_after or not choice_prompt:
      code = ''
    else:
      # Wait for a prompt before the operation.
      code = '    self.read_until({})\n'.format(repr(get_postfix(choice_prompt)))

    code += '    self.write({})\n'.format(repr(choice_str))

    # For each possible field.
    for i in range(1, len(stdio_trace_by_type[TYPE_STDIN])):
      raw_prompt = stdio_trace_by_type[TYPE_STDOUT][i][1]
      prompt = raw_prompt.decode()
      raw_input = stdio_trace_by_type[TYPE_STDIN][i][1]
      input = raw_input.decode()
      scores = {'ref': 0, 'size': 0, 'buffer': 0}
      # Keyword-based semantic-aware field type recognition.
      if list_in_str(REF_KEYWORDS, prompt.lower()):
        scores['ref'] += 10
      if list_in_str(SIZE_KEYWORDS, prompt.lower()):
        scores['size'] += 10
      if list_in_str(BUFFER_KEYWORDS, prompt.lower()):
        scores['buffer'] += 10
      try:
        # Is the input an integer? Did it appear in the allocator trace?
        if _size_in_trace(int(input.strip()), slice):
          scores['size'] += 1
      except ValueError:
        pass
      # Or, did its length appear in the allocator trace?
      if _size_in_trace(len(input), slice) or \
         _size_in_trace(len(input) - 1, slice) or \
         _size_in_trace(len(input) + 1, slice):
        scores['buffer'] += 1
      clog('debug', 'Scores: {}', scores)
      type, max_score = max(scores.items(), key=lambda t: t[1])
      if max_score > 0:
        clog('info', 'The field with prompt {} is considered as a {}.', repr(prompt), type)
      else:
        clog('info', 'The field with prompt {} is not a field.', repr(prompt))
      code += '    self.read_until({})\n'.format(repr(get_postfix(raw_prompt)))
      if max_score == 0:
        code += '    self.write({})\n'.format(repr(raw_input))
      elif type == 'ref':
        code += "    self.write(ref + b'\\n')\n"
      elif type == 'size':
        code += "    self.write(str(size).encode() + b'\\n')\n"
      elif type == 'buffer':
        code += "    self.write(str('A' * size).encode() + b'\\n')\n"
      else:
        assert(False)

    # For the return value.
    has_return = False
    has_unknown_return = False
    if len(stdio_trace_by_type[TYPE_STDOUT]) > len(stdio_trace_by_type[TYPE_STDIN]):
      clog('info', 'A possible return value detected.')
      assert(len(stdio_trace_by_type[TYPE_STDOUT]) == len(stdio_trace_by_type[TYPE_STDIN]) + 1)
      # Parse return value.
      remaining_stdout = stdio_trace_by_type[TYPE_STDOUT][len(stdio_trace_by_type[TYPE_STDIN])][1]
      match = REF_RE.match(remaining_stdout)
      if match:
        prefix = match.group(1)
        ref = match.group(2)
        postfix = match.group(5)
        assert(bool(postfix))
        code += '    # {} ???? {}\n'.format(repr(prefix.decode()), repr(postfix.decode()))
        code += '    ret = self.read_until({})[{}:{}]\n' \
                .format(repr(get_postfix(postfix)),
                        len(prefix) if len(prefix) else '', -len(postfix))
        has_return = True
      else:
        clog('info', 'Unknown format of the return value.')
        has_unknown_return = bool(remaining_stdout.strip())  # has visible characters.
    else:
      clog('info', 'No return value found.')

    # Wait for a prompt after the operation to ensure this operation is done.
    if read_prompt_after and choice_prompt:
      code += '    self.read_until({})\n'.format(repr(get_postfix(choice_prompt)))

    if has_return:
      code += '    return ret\n'
    if has_unknown_return:
      code += '    # TODO: deal with the possible return value\n'

    # Commit.
    if score > 0:
      # malloc
      clog('info', 'The above slice is considered as a malloc operation.')
      gen.add_malloc(code)
    elif score < 0:
      # free
      clog('info', 'The above slice is considered as a free operation.')
      gen.add_free(code)
    else:
      clog('warn', 'Do not know how to deal with the above slice, skipping.')
      # score == 0
      # TODO: determine whether this is a malloc or free.
      pass
  clog('info', 'Emitting...')
  return gen.gen()


def main():
  try:
    os.makedirs(args.output)
  except FileExistsError:
    pass
  executable = os.path.realpath(args.args[0])
  if args.loop == 'off' or args.loop == 'no':
    hook_addr = None
  elif args.loop == 'auto':
    if args.ida:
      main_func, main_loop = loop_finder.find_loop_ida(args.ida, executable, args.output)
    else:
      assert(bool(args.retdec))
      main_func, main_loop = loop_finder.find_loop_retdec(args.retdec, executable, args.output)
    hook_addr = main_loop
  else:
    hook_addr = int(args.loop, 16)  # 0x998 # 0x924  # FIXME: magic
  clog('info', 'Start a fork server.')
  forkd = server.ForkServer(True, args.args, args.allocator)
  if hook_addr != None:
    clog('info', 'Setting a hook at {}.', hex(hook_addr))
    forkd.hook_addr = hook_addr
  forkd.init()
  child_info = forkd.fork()
  ator = allocator.AbstractAllocator()
  ator.record_full_trace = True
  ator.attach(*child_info)
  epoll = select.epoll(2)
  set_nonblock(sys.stdin.fileno(), True)
  epoll.register(sys.stdin.fileno(), select.EPOLLIN)
  epoll.register(forkd.epoll.fileno(), select.EPOLLIN)
  clog('ok', 'Start interaction.')
  try:
    while True:
      events = epoll.poll()
      if (sys.stdin.fileno(), select.EPOLLIN) in events:
        data = read_leftovers(sys.stdin.fileno(), is_already_nonblock=True)
        if not data:
          clog('warn', 'stdin stream closed.')
        if not sys.stdin.isatty():
          my_print(data)
        ator.write(data)
      if (forkd.epoll.fileno(), select.EPOLLIN) in events:
        my_print(ator.read_leftovers())
  except allocator.ExitingError:
    pass
  clog('info', 'Exited.')
  ator.fix_output_trace()
  write_results(args.output, ator, None, "tracer's ", '', True)
  slices = trace.trace_slice(ator.full_trace)
  spec_code = slices_to_spec(slices)
  with open('{}/spec.py'.format(args.output), 'w') as f:
    f.write(spec_code)
  clog('ok', 'The spec code is written to {}/spec.py.', args.output)
  forkd.kill()
  forkd.wait_for_exit()
  clog('ok', 'Done.')
  return 0


if __name__ == '__main__':
  args = parser.parse_args()
  exit(main())
