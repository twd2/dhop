import json
import os
import subprocess
import sys


def find_loop_ida(ida_dir, executable, result_dir):
  print('[INFO] Start analyzing the input file using IDA Pro...')
  raise NotImplementedError()


def find_loop_retdec(retdec_dir, executable, result_dir):
  current_dir = os.path.dirname(os.path.realpath(__file__))
  result_file = result_dir + '/retdec.ll'

  print('[INFO] Start analyzing the input file using RetDec...')
  sys.stdout.flush()
  retdec_result = subprocess.run(['python3', retdec_dir + '/bin/retdec-decompiler.py',
                                  '--stop-after', 'bin2llvmir', '-o', result_file, executable])
  if retdec_result.returncode != 0:
    print('[ERROR] RetDec failed.')
    exit(1)
  print('[INFO] Finding the main loop in the input file...')
  sys.stdout.flush()
  lf_result = subprocess.run([current_dir + '/loop-finder/build/loop-finder', result_file],
                             stdout=subprocess.PIPE, encoding='UTF-8')
  if lf_result.returncode != 0:
    print('[ERROR] Loop finder failed.')
    exit(1)
  lf_out = lf_result.stdout
  print('[DEBUG] Loop finder\'s output:')
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

  with open(result_file[:-2] + 'json', 'r') as f:
    obj = json.load(f)
    entry_point = int(obj['entryPoint'], 16)
  print('[INFO] The entry point is at {}.'.format(hex(entry_point)))
  if main_func != None:
    print('[INFO] The main function is at {}.'.format(hex(main_func)))
  else:
    print('[WARN] The main function is not found. :(')
  if main_loop != None:
    print('[INFO] The entry basic block of the main loop should be at {}.'.format(hex(main_loop)))
  else:
    print('[WARN] The main loop is not found. :(')
  return entry_point, main_func, main_loop


if __name__ == '__main__':
  # print(find_loop_ida('/home/twd2/ida-6.8', sys.argv[1], 'results'))
  print(find_loop_retdec('/opt/retdec', sys.argv[1], 'results'))
