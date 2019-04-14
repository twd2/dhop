import fcntl
import os
import struct


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

