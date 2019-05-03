import fcntl
import os
import struct
import subprocess


INSPECT_FD = 3
SERVER_FD  = 4
TYPE_READY    = 0
TYPE_PID      = 1
TYPE_MALLOC   = 2
TYPE_CALLOC   = 3
TYPE_REALLOC  = 4
TYPE_FREE     = 5
TYPE_EXIT     = 6
STRUCT_PACKET = '<QQQQ'
SIZEOF_PACKET = len(struct.pack(STRUCT_PACKET, 0, 0, 0, 0))

TYPE_MAIN_LOOP = 1000
TYPE_STDIN    = 10000
TYPE_STDOUT   = 10001


def find_section_text(executable):
  result = subprocess.run(['objdump', '-p', executable], env={**os.environ, 'LANG': 'en_US'},
                          stdout=subprocess.PIPE, encoding='UTF-8')
  if result.returncode != 0:
    clog('error', 'objdump failed.')
    exit(1)
  lines = result.stdout.split('\n')
  it = iter(lines)
  while not next(it).startswith('Program Header:'): pass
  while True:
    line1 = next(it).strip()
    if not line1:
      break
    line2 = next(it).strip()
    vmbegin = int(line1.split()[4], 16)
    prot = line2.split()[5]
    if 'x' in prot:
      return vmbegin
  return None


def read_packet(fd):
  buff = os.read(fd, SIZEOF_PACKET)
  return struct.unpack(STRUCT_PACKET, buff)


def unpack_packets(data):
  assert(len(data) % SIZEOF_PACKET == 0)
  packets = [0] * (len(data) // SIZEOF_PACKET)
  j = 0
  for i in range(0, len(packets)):
    packets[i] = struct.unpack(STRUCT_PACKET, data[j:j + SIZEOF_PACKET])
    j += SIZEOF_PACKET
  return packets


def get_nonblock(fd):
  flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
  return bool(flags & os.O_NONBLOCK)


def set_nonblock(fd, nonblock):
  flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
  fcntl.fcntl(fd, fcntl.F_SETFL, (flags & ~os.O_NONBLOCK) | (os.O_NONBLOCK if nonblock else 0))


def read_leftovers(fd, is_already_nonblock=False):
  if not is_already_nonblock:
    saved_flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    fcntl.fcntl(fd, fcntl.F_SETFL, saved_flags | os.O_NONBLOCK)
  buff = b''
  try:
    while True:
      chunk = os.read(fd, 4096)
      if len(chunk) <= 0:
        break
      buff += chunk
  except BlockingIOError:
    pass
  if not is_already_nonblock:
    fcntl.fcntl(fd, fcntl.F_SETFL, saved_flags)
  return buff


def get_postfix(s, min_len=4):
  # Get a postfix with the minimum length being min_len and having not appeared before.
  postfix = s[-min_len:]
  while postfix in s[:-1]:
    min_len += 1
    postfix = s[-min_len:]
  return postfix


def list_in_str(l, s):
  for item in l:
    if item in s:
      return True
  return False


def clog(level, s, *args, end=None):
  if level:
    level = level.upper()
    color_map = {'DEBUG': '\033[0;37m', 'INFO': '\033[1;37m', 'WARN': '\033[1;33m',
                 'ERROR': '\033[1;31m', 'OK': '\033[1;32m'}
    print('{}[{}]{} {}'.format(color_map.get(level, ''), level, '\033[0m',
                               s.format(*args) if args else s), end=end)
  else:
    print(s.format(*args) if args else s, end=end)
