#!/usr/bin/env python3

import argparse
import copy
import math
import os
import os.path
import pkgutil
import random
import sys
import time

import allocator
import opseq
import server
import trace


parser = argparse.ArgumentParser()
parser.add_argument('-a', '--allocator', help='specify the allocator library (.so)')
parser.add_argument('-n', '--no-optimize', action='store_true', help='do not optimize results')
parser.add_argument('-o', '--output', default='results/unnamed',
                    help='specify the result directory, default: results')
parser.add_argument('-s', '--solver', default='random', choices=['random', 'directed', 'diversity'],
                    help='specify the solver, default is the random solver')
parser.add_argument('-t', '--timeout', type=int, default=600, help='timeout (seconds), default: 600')
parser.add_argument('-z', '--solver-args', nargs='*', default=[], help='executable and its arguments')
parser.add_argument('spec', help='specify the description (spec) file')
parser.add_argument('args', nargs='+', help='executable and its arguments')


def get_class(type, module_name, class_name):
  model_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), type)
  for module_finder, name, ispkg in pkgutil.iter_modules([model_path]):
    if name != module_name:
      continue
    if not ispkg:
      module = module_finder.find_module(name).load_module()
      if class_name in dir(module):
        return getattr(module, class_name)
  return None


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
      print('[INFO] The {}operations sequence is written to {}/{}opseq.txt.' \
            .format(adj, result_dir, prefix))
  with open('{}/{}input.txt'.format(result_dir, prefix), 'wb') as f:
    f.write(b''.join(ator.input_trace))
    print('[INFO] The {}input is written to {}/{}input.txt.'.format(adj, result_dir, prefix))
  with open('{}/{}trace.txt'.format(result_dir, prefix), 'w') as f:
    trace.dump_trace(f, ator.allocator_trace)
    print('[INFO] The {}trace is written to {}/{}trace.txt.'.format(adj, result_dir, prefix))
  if write_full_trace:
    with open('{}/{}full_trace.txt'.format(result_dir, prefix), 'w') as f:
      trace.dump_trace(f, ator.full_trace)
      print('[INFO] The {}full trace is written to {}/{}full_trace.txt.' \
            .format(adj, result_dir, prefix))
  with open('{}/{}layout.txt'.format(result_dir, prefix), 'w') as f:
    trace.dump_layout(f, trace.trace_to_layout(ator.allocator_trace), ator.a_addr, ator.b_addr)
    print('[INFO] The {}layout is written to {}/{}layout.txt.'.format(adj, result_dir, prefix))


def main():
  ator_spec = get_class('spec', args.spec, 'Allocator')
  if not ator_spec:
    print('[ERROR] No such spec named "{}".'.format(args.spec))
    exit(1)
  Solver = get_class('solver', args.solver, 'Solver')
  if not Solver:
    print('[ERROR] No such solver named "{}".'.format(args.solver))
    exit(1)
  do_optimize = not args.no_optimize
  new_seed_ratio = 1#0.5  # FIXME
  try:
    os.makedirs(args.output)
  except FileExistsError:
    pass
  solver = Solver(*args.solver_args)
  print('[INFO] Start')
  forkd = server.ForkServer(args.args, args.allocator)
  forkd.wait_for_ready()
  seed_count = 0
  eps = 0
  total = 0
  crashes = 0
  min_loss = 0xffffffffffffffff
  done = False
  solved = False
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
      if ator:
        loss = ator.loss()
        if loss == 0:
          end_time = time.time()
          print('\n[INFO] loss = 0\n[INFO] Congratulations! The desired heap layout is achieved.')
          write_results(args.output, ator, ops)
          if do_optimize:
            print('[INFO] Optimizing results... ', end='')
            ator, ops = optimize_ops(forkd, ator_spec, ops)
            print('done!')
            write_results(args.output, ator, ops, 'optimized ', 'opt_')
          solved = True
          done = True
          break
        solver.update_result(ops, ator)
        if loss < min_loss:
          min_loss = loss
      eps += 1
      total += 1
      current_time = time.time()
      if current_time - last_time >= 1.0:
        last_time = current_time
        print('\r[INFO] {} executions / sec, {} crashes, {} executions totally, loss = {}    '
              .format(eps, crashes, total, min_loss), end='')
        eps = 0
        if current_time - begin_time >= args.timeout:
          end_time = time.time()
          print('\n[WARN] Timed out.')
          solved = False
          done = True
          break
  forkd.kill()
  forkd.wait_for_exit()
  time_usage = end_time - begin_time
  print('[INFO] {} crashes, {} executions totally, {:.6f} seconds, {:.2f} executions / sec'
        .format(crashes, total, time_usage, total / time_usage))
  with open('{}/stat.csv'.format(args.output), 'w') as f:
    f.write('{},{},{},{},{},{},{},{},{},{},{}\n'.format(
              args.allocator if args.allocator else 'system default',
              args.solver,
              ' '.join(args.solver_args),
              args.timeout,
              args.spec,
              ' '.join(args.args),
              int(solved),
              crashes,
              total,
              time_usage,
              total / time_usage
            ))
  print('[INFO] The summary is written to {}/stat.csv.'.format(args.output))
  print('[INFO] Exiting...')
  return 0


if __name__ == '__main__':
  args = parser.parse_args()
  exit(main())
