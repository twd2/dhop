import json
import os
import subprocess
import sys

from utils import *


_current_dir = os.path.dirname(os.path.realpath(__file__))


def find_loop_mcsema(mcsema_dir, ida_dir, executable, result_dir):
  clog('info', 'Start recovering the CFG of the input file using McSema...')
  sys.stdout.flush()
  cfg_file = result_dir + '/mcsema_cfg.pb'
  log_file = result_dir + '/mcsema_log.txt'
  mcsema_result = subprocess.run([mcsema_dir + '/bin/mcsema-disass', '--disassembler',
                                  ida_dir + '/idal64', '--arch', 'amd64', '--os', 'linux',
                                  '--output', cfg_file, '--binary', executable, '--entrypoint',
                                  '_start', '--log_file', log_file],
                                  env={'PYTHONPATH': mcsema_dir + '/lib/python2.7/site-packages',
                                       **os.environ})
  if mcsema_result.returncode != 0:
    clog('error', 'mcsema-disass failed.')
    exit(1)
  clog('info', 'Start lifting the input file using McSema...')
  sys.stdout.flush()
  result_file = result_dir + '/mcsema.bc'
  mcsema_result = subprocess.run([mcsema_dir + '/bin/mcsema-lift-6.0', '--arch', 'amd64',
                                  '--os', 'linux', '--cfg', cfg_file, '--output', result_file])
  if mcsema_result.returncode != 0:
    clog('error', 'mcsema-lift failed.')
    exit(1)
  clog('info', 'Finding the main loop in the LLVM IR...')
  sys.stdout.flush()
  lf_result = subprocess.run([_current_dir + '/loop-finder/build/loop-finder', result_file],
                             stdout=subprocess.PIPE, encoding='UTF-8')
  if lf_result.returncode != 0:
    clog('error', 'Loop finder failed.')
    exit(1)
  lf_out = lf_result.stdout
  clog('debug', 'Loop finder\'s output:')
  print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
  print(lf_out)
  print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
  raise NotImplementedError()


def find_loop_retdec(retdec_dir, executable, result_dir):
  clog('info', 'Start lifting the input file using RetDec...')
  sys.stdout.flush()
  result_file = result_dir + '/retdec.ll'
  retdec_result = subprocess.run(['python3', retdec_dir + '/bin/retdec-decompiler.py',
                                  '--stop-after', 'bin2llvmir', '-o', result_file, executable])
  if retdec_result.returncode != 0:
    clog('error', 'RetDec failed.')
    exit(1)
  clog('info', 'Finding the main loop in the LLVM IR...')
  sys.stdout.flush()
  lf_result = subprocess.run([_current_dir + '/loop-finder/build/loop-finder', result_file],
                             stdout=subprocess.PIPE, encoding='UTF-8')
  if lf_result.returncode != 0:
    clog('error', 'Loop finder failed.')
    exit(1)
  lf_out = lf_result.stdout
  clog('debug', 'Loop finder\'s output:')
  print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
  print(lf_out)
  print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')

  main_func = None
  main_loop = None
  for line in lf_out.split('\n'):
    parts = line.split()
    if len(parts) < 3:
      continue
    if parts[1] == 'main' and 'not found' not in line:
      main_func = int(parts[-1], 16)
    if parts[1] == 'entry':
      main_loop = int(parts[-1], 16)

  if main_func != None:
    clog('info', 'The main function is at {}.', hex(main_func))
  else:
    clog('warn', 'The main function is not found. :(')
  if main_loop != None:
    clog('info', 'The entry basic block of the main loop should be at {}.', hex(main_loop))
  else:
    clog('warn', 'The main loop is not found. :(')
  return main_func, main_loop


if __name__ == '__main__':
  print(hex(find_section_text(sys.argv[1])))
  print(find_loop_mcsema('/opt/mcsema', '/home/twd2/ida-6.8', sys.argv[1], 'results'))
  #print(find_loop_retdec('/opt/retdec', sys.argv[1], 'results'))
