import os
import pty
import select
import signal
import struct
import sys

from utils import *


# Fork Server - client side
class ForkServer():
  def __init__(self, do_hook, args, malloc_so=None):
    self.do_hook = do_hook
    self.args = args
    self.malloc_so = malloc_so
    self.executable = os.path.realpath(args[0])
    self.hook_addr = None
    inspect_fd_r, inspect_fd_w = os.pipe2(0)
    server_fd_r, server_fd_w = os.pipe2(0)
    stdin_fd_r, stdin_fd_w = os.pipe2(0)
    stdout_fd_r, stdout_fd_w = os.pipe2(0)
    server_pid = os.fork()
    if not server_pid:
      # child
      if inspect_fd_w == INSPECT_FD:
        os.set_inheritable(inspect_fd_w, True)
      else:
        os.dup2(inspect_fd_w, INSPECT_FD)
        os.close(inspect_fd_w)
      if server_fd_r == SERVER_FD:
        os.set_inheritable(server_fd_r, True)
      else:
        os.dup2(server_fd_r, SERVER_FD)
        os.close(server_fd_r)
      os.dup2(stdin_fd_r, pty.STDIN_FILENO)
      if stdin_fd_r != pty.STDIN_FILENO:
        os.close(stdin_fd_r)
      os.dup2(stdout_fd_w, pty.STDOUT_FILENO)
      os.dup2(stdout_fd_w, pty.STDERR_FILENO)
      if stdout_fd_w != pty.STDOUT_FILENO and stdout_fd_w != pty.STDERR_FILENO:
        os.close(stdout_fd_w)
      if do_hook:
        preload_libraries = [os.path.dirname(os.path.realpath(__file__)) + '/wrapper_hook.so']
      else:
        preload_libraries = [os.path.dirname(os.path.realpath(__file__)) + '/wrapper.so']
      if malloc_so:
        preload_libraries.append(malloc_so)
      os.execve(args[0], args, {**os.environ, 'LD_PRELOAD': ':'.join(preload_libraries)})
      assert(False)
    else:
      # parent
      self.server_pid = server_pid
      self.inspect_fd = inspect_fd_r
      self.server_fd = server_fd_w
      self.stdin_fd = stdin_fd_w
      self.stdout_fd = stdout_fd_r

  def wait_for_ready(self):
    clog('info', 'Waiting for the fork server... ', end='')
    sys.stdout.flush()
    events = self.epoll.poll()
    if events != [(self.inspect_fd, select.EPOLLIN)]:
      clog('', 'something goes wrong. :(')
      clog('debug', 'Output of the fork server:')
      while True:
        print(read_leftovers(self.stdout_fd, is_already_nonblock=True).decode(), end='')
        self.epoll.poll()
    while True:
      type, _, _, _ = read_packet(self.inspect_fd)
      if type == TYPE_READY:
        break
      self.epoll.poll()
    clog('', 'ready!')

  def _find_section_text(self):
    # Find Section text in the image (ELF file).
    self.exe_section_text_begin = find_section_text(self.executable)
    clog('info', 'Section .text is beginning at {} in the image (ELF file).',
         hex(self.exe_section_text_begin))
    # Find Section text in the child process.
    self.proc_section_text_begin = 0
    with open('/proc/{}/maps'.format(self.server_pid), 'r') as f:
      for line in f:
        # 555555554000-55555555c000 r-xp 00000000 08:02 5242960                    /bin/cat
        parts = line.split()
        vmrange, prot, filename = parts[0], parts[1], parts[5] if len(parts) >= 6 else ''
        vmbegin, vmend = vmrange.split('-')
        vmbegin = int(vmbegin, 16)
        vmend = int(vmend, 16)
        if 'x' in prot and os.path.realpath(filename) == self.executable:
          self.proc_section_text_begin = vmbegin
          break
    clog('info', 'Section .text is beginning at {}.', hex(self.proc_section_text_begin))

  def _set_hook(self):
    if self.hook_addr != None:
      hook_addr = self.hook_addr - self.exe_section_text_begin + self.proc_section_text_begin
    else:
      hook_addr = 0
    os.write(self.server_fd, struct.pack('<Q', hook_addr))

  def init(self):
    clog('debug', 'fork server pid is {}.', self.server_pid)
    # Create an epoll object for 2 fds.
    fds = [self.inspect_fd, self.stdout_fd]
    self.epoll = select.epoll(len(fds))
    for fd in fds:
      set_nonblock(fd, True)
      self.epoll.register(fd, select.EPOLLIN)
    if self.do_hook:
      self.wait_for_ready()
      self._find_section_text()
      self._set_hook()
    self.wait_for_ready()

  def fork(self):
    read_leftovers(self.inspect_fd, is_already_nonblock=True)
    read_leftovers(self.stdout_fd, is_already_nonblock=True)
    # Send a request.
    os.write(self.server_fd, b'A')  # an arbitrary char
    # FIXME: ugly
    while True:
      events = []
      while (self.inspect_fd, select.EPOLLIN) not in events:
        if (self.stdout_fd, select.EPOLLIN) in events:
          clog('debug', 'What\'s this? {}',
               read_leftovers(self.stdout_fd, is_already_nonblock=True))
        events = self.epoll.poll()
      type, _, _, child_pid = read_packet(self.inspect_fd)
      if type == TYPE_PID:
        # clog('info', 'child pid {}', child_pid)
        break
      else:
        clog('warn', 'something wrong, received type {} rather than TYPE_READY.', type)
    # Allow the child to continue.
    os.write(self.server_fd, b'A')  # an arbitrary char
    return child_pid, self.inspect_fd, self.stdin_fd, self.stdout_fd, self.epoll

  def kill(self):
    os.kill(self.server_pid, signal.SIGKILL)

  def wait_for_exit(self):
    os.waitpid(self.server_pid, 0)
