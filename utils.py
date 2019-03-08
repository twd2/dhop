import os
import fcntl

def get_nonblock(fd):
  flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
  return bool(flags & os.O_NONBLOCK)

def set_nonblock(fd, nonblock):
  flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
  fcntl.fcntl(fd, fcntl.F_SETFL, (flags & ~os.O_NONBLOCK) | (os.O_NONBLOCK if nonblock else 0))

def read_leftovers(fd):
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
  fcntl.fcntl(fd, fcntl.F_SETFL, saved_flags)
  return buff

