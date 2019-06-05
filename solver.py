#!/usr/bin/env python3

import argparse
import copy
import gc
import importlib.util
import math
import os
import os.path
import random
import sys
import time

import allocator
import opseq
import server
import trace

from utils import *


parser = argparse.ArgumentParser()
parser.add_argument('-a', '--allocator', help='specify the allocator library (.so)')
parser.add_argument('-n', '--no-optimize', action='store_true', help='do not optimize results')
parser.add_argument('-o', '--output', default='results/unnamed',
                    help='specify the result directory, default: results')
parser.add_argument('-s', '--solver', default='random', choices=['random', 'directed', 'diversity'],
                    help='specify the solver, default is the random solver')
parser.add_argument('-t', '--timeout', type=int, default=600, help='timeout (seconds), default: 600')
parser.add_argument('-m', '--maxexe', type=int, default=0,
                    help='max executions, default: 0 (unlimited)')
parser.add_argument('-z', '--solver-args', nargs='*', default=[], help='executable and its arguments')
parser.add_argument('spec', help='specify the description (spec) file')
parser.add_argument('args', nargs='+', help='executable and its arguments')


def load_class(module_name, filename, class_name):
  spec = importlib.util.spec_from_file_location(module_name, filename)
  if not spec:
    return None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  if class_name not in dir(module):
    return None
  return getattr(module, class_name)


def execute_ops(forkd, ator_spec, ops):
  child_info = forkd.fork()
  ator = ator_spec()
  ator.attach(*child_info)
  ator.init()
  ator.execute(ops)
  ator.kill()
  ator.wait()
  return ator


def optimize_ops(forkd, ator_spec, ops):
  dirty = True
  while dirty:
    dirty = False
    for i, (type, _, _) in enumerate(ops):
      if type == opseq.HeapOpType.A or type == opseq.HeapOpType.B:
        continue
      # Try to remove
      new_ops = copy.deepcopy(ops)
      new_ops = opseq.remove_op(new_ops, i)
      try:
        # and check
        ator = execute_ops(forkd, ator_spec, new_ops)
        if ator.loss() == 0:
          # If loss is still zero, this op can be removed.
          dirty = True
          ops = new_ops
          break
      except allocator.ExitingError:
        pass
  ator = execute_ops(forkd, ator_spec, ops)
  return ator, ops


def write_results(result_dir, ator, ops, adj='', prefix='', write_full_trace=False):
  if ops != None:
    with open('{}/{}opseq.txt'.format(result_dir, prefix), 'w') as f:
      opseq.dump_ops(f, ops)
    clog('ok', 'The {}operations sequence is written to {}/{}opseq.txt.', adj, result_dir, prefix)
  if ator.a_ref != None or ator.b_ref != None:
    with open('{}/{}ref.txt'.format(result_dir, prefix), 'w') as f:
      if ator.a_ref != None:
        f.write('The reference of the allocation A is {}.\n'.format(repr(ator.a_ref)))
      if ator.b_ref != None:
        f.write('The reference of the allocation B is {}.\n'.format(repr(ator.b_ref)))
    clog('ok', 'The {}references are written to {}/{}ref.txt.', adj, result_dir, prefix)
  with open('{}/{}input.txt'.format(result_dir, prefix), 'wb') as f:
    f.write(b''.join(ator.input_trace))
  clog('ok', 'The {}input is written to {}/{}input.txt.', adj, result_dir, prefix)
  with open('{}/{}trace.txt'.format(result_dir, prefix), 'w') as f:
    trace.dump_trace(f, ator.allocator_trace)
  clog('ok', 'The {}trace is written to {}/{}trace.txt.', adj, result_dir, prefix)
  with open('{}/{}code.c'.format(result_dir, prefix), 'w') as f:
    trace.trace_to_code(f, ator.allocator_trace)
  clog('ok', 'The {}code to reproduce this trace is written to {}/{}code.c.',
       adj, result_dir, prefix)
  if write_full_trace:
    with open('{}/{}full_trace.txt'.format(result_dir, prefix), 'w') as f:
      trace.dump_trace(f, ator.full_trace)
    clog('ok', 'The {}full trace is written to {}/{}full_trace.txt.', adj, result_dir, prefix)
  with open('{}/{}layout.txt'.format(result_dir, prefix), 'w') as f:
    trace.dump_layout(f, trace.trace_to_layout(ator.allocator_trace), ator.a_addr, ator.b_addr)
  clog('ok', 'The {}layout is written to {}/{}layout.txt.', adj, result_dir, prefix)


def main():
  clog('info', 'The target executable is "{}".', args.args[0])
  ator_spec = load_class('spec', args.spec, 'Allocator')
  if not ator_spec:
    clog('error', 'No such spec named "{}".', args.spec)
    exit(1)
  else:
    clog('info', 'Using spec named "{}".', args.spec)
  Solver = load_class('solver', 'solver/{}.py'.format(args.solver), 'Solver')
  if not Solver:
    clog('error', 'No such solver named "{}".', args.solver)
    exit(1)
  else:
    clog('info', 'Using solver named "{}".', args.solver)
  clog('info', 'Using allocator "{}".', args.allocator if args.allocator else '(system default)')
  do_optimize = not args.no_optimize
  try:
    os.makedirs(args.output)
  except FileExistsError:
    pass
  clog('info', 'Results will be written to "{}".', args.output)
  solver = Solver(*args.solver_args)
  clog('info', 'Start')
  forkd = server.ForkServer(False, args.args, args.allocator)
  forkd.init()
  seed_count = 0
  eps = 0
  total = 0
  crashes = 0
  min_loss = 0xffffffffffffffff
  done = False
  solved = False
  solution_size = 0
  opt_solution_size = 0
  begin_time = time.time()
  last_time = begin_time
  while not done:
    candidates = solver.get_candidates()
    for ops in candidates:
      ator = None
      try:
        ator = execute_ops(forkd, ator_spec, ops)
      except allocator.ExitingError:
        crashes += 1
      eps += 1
      total += 1
      if ator:
        loss = ator.loss()
        if loss < min_loss:
          min_loss = loss
        if loss == 0:
          end_time = time.time()
          clog('', '')
          clog('info', 'loss = 0')
          clog('ok', 'Congratulations! The desired heap layout is achieved.')
          solution_size = len(ops)
          clog('info', 'The size of the solution is {}.', solution_size)
          write_results(args.output, ator, ops)
          if do_optimize:
            clog('info', 'Optimizing results... ', end='')
            ator, ops = optimize_ops(forkd, ator_spec, ops)
            clog('', 'done!')
            opt_solution_size = len(ops)
            clog('info', 'The size of the optimized solution is {}.', opt_solution_size)
            write_results(args.output, ator, ops, 'optimized ', 'opt_')
          solved = True
          done = True
          break
        solver.update_result(ops, ator)
      current_time = time.time()
      if current_time - last_time >= 1.0:
        gc.collect()
        last_time = current_time
        clog('', '\r', end='')
        clog('info', '{} executions / sec, {} crashes, {} executions totally, loss = {}    ',
             eps, crashes, total, min_loss, end='')
        eps = 0
        if args.timeout and current_time - begin_time >= args.timeout:
          end_time = time.time()
          clog('', '')
          clog('warn', 'Timed out.')
          solved = False
          done = True
          break
        if args.maxexe and total >= args.maxexe:
          end_time = time.time()
          clog('', '')
          clog('warn', 'Executions limit reached.')
          solved = False
          done = True
          break
  forkd.kill()
  forkd.wait_for_exit()
  time_usage = end_time - begin_time
  clog('info', '{} crashes, {} executions totally, {:.6f} seconds, {:.2f} executions / sec',
       crashes, total, time_usage, total / time_usage)
  with open('{}/stat.csv'.format(args.output), 'w') as f:
    f.write('{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(
              args.output,
              args.allocator if args.allocator else '(system default)',
              args.solver,
              ' '.join(args.solver_args) if args.solver_args else '(default)',
              args.timeout,
              args.spec,
              ' '.join(args.args),
              int(solved),
              min_loss,
              total,
              crashes,
              time_usage,
              total / time_usage,
              solution_size,
              opt_solution_size,
              opt_solution_size / solution_size if solution_size else 0,
            ))
  clog('ok', 'The summary is written to {}/stat.csv.', args.output)
  clog('info', 'Exiting...')
  return 0


if __name__ == '__main__':
  args = parser.parse_args()
  exit(main())
