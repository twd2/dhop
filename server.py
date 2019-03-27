import os
import pty
import select
import signal
import sys

from utils import *


# Fork Server - client side
class ForkServer():
  def __init__(self, args):
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
      os.execve(args[0], args,
                {**os.environ,
                 'LD_PRELOAD': os.path.dirname(os.path.realpath(__file__)) + '/wrapper.so'})
      assert(False)
    else:
      # parent
      self.server_pid = server_pid
      self.inspect_fd = inspect_fd_r
      self.server_fd = server_fd_w
      self.stdin_fd = stdin_fd_w
      self.stdout_fd = stdout_fd_r

  def wait_for_ready(self):
    # Create an epoll object for 2 fds.
    set_nonblock(self.inspect_fd, True)
    set_nonblock(self.stdout_fd, True)
    fds = [self.inspect_fd, self.stdout_fd]
    self.epoll = select.epoll(len(fds))
    for fd in fds:
      set_nonblock(fd, True)
      self.epoll.register(fd, select.EPOLLIN)
    print('[INFO] Waiting for the fork server... ', end='')
    sys.stdout.flush()
    events = self.epoll.poll()
    if events != [(self.inspect_fd, select.EPOLLIN)]:
      print('something goes wrong. :(\n[DEBUG] Output of the fork server:')
      while True:
        print(read_leftovers(self.stdout_fd, is_already_nonblock=True).decode(), end='')
        self.epoll.poll()
    type, _, _, _ = read_packet(self.inspect_fd)
    assert(type == TYPE_READY)
    print('ready!')
    print('[DEBUG] fork server pid is', self.server_pid)

  def fork(self):
    read_leftovers(self.inspect_fd, is_already_nonblock=True)
    read_leftovers(self.stdout_fd, is_already_nonblock=True)
    os.write(self.server_fd, b'A')  # an arbitrary char
    # FIXME: ugly
    while True:
      events = []
      while (self.inspect_fd, select.EPOLLIN) not in events:
        events = self.epoll.poll()
      type, _, _, child_pid = read_packet(self.inspect_fd)
      if type == TYPE_PID:
        # print('[INFO] child pid', child_pid)
        break
      else:
        # print('[WARN] something wrong')
        pass
    return child_pid, self.inspect_fd, self.stdin_fd, self.stdout_fd, self.epoll

  def kill(self):
    os.kill(self.server_pid, signal.SIGKILL)

  def wait_for_exit(self):
    os.waitpid(self.server_pid, 0)
