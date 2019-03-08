#define _GNU_SOURCE

#include <sys/types.h>
#include <sys/wait.h>
#include <signal.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <dlfcn.h>

#define INSPECT_FD 3
#define SERVER_FD  4
#define FORK_SERVER 1

#define TYPE_READY    0
#define TYPE_PID      1
#define TYPE_MALLOC   2
#define TYPE_CALLOC   3
#define TYPE_REALLOC  4
#define TYPE_FREE     5
#define TYPE_WAIT     6

typedef struct
{
  size_t type;
  size_t arg1, arg2;
  size_t ret;
} packet_t;

static void *boot_malloc(size_t size);
static void *boot_calloc(size_t num, size_t size);
static void *boot_realloc(void *ptr, size_t size);
static void boot_free(void *ptr);

#ifdef FORK_SERVER
static void fork_server(void);
#endif

static char initialized = 0;
static char tmp[4096] = { 0 };
static size_t ptr = 0;

static void *(*orig_malloc)(size_t size) = boot_malloc;
static void *(*orig_calloc)(size_t num, size_t size) = boot_calloc;
static void *(*orig_realloc)(void *ptr, size_t size) = boot_realloc;
static void (*orig_free)(void *ptr) = boot_free;

static void init(void)
{
  initialized = 1;
  orig_malloc = dlsym(RTLD_NEXT, "malloc");
  orig_calloc = dlsym(RTLD_NEXT, "calloc");
  orig_realloc = dlsym(RTLD_NEXT, "realloc");
  orig_free = dlsym(RTLD_NEXT, "free");
  (void)dlsym(RTLD_NEXT, "puts");
  (void)dlsym(RTLD_NEXT, "printf");
  (void)dlsym(RTLD_NEXT, "scanf");
  (void)dlsym(RTLD_NEXT, "exit");
#ifdef FORK_SERVER
  fork_server();
#endif
}

static void ctor(void) __attribute__((constructor));
static void ctor(void)
{
  init();
}

static void *boot_malloc(size_t size)
{
  ptr += size;
  return (void *)&tmp[ptr - size];
}

static void *boot_calloc(size_t num, size_t size)
{
  size *= num;
  return boot_malloc(size);
}

static void *boot_realloc(void *ptr, size_t size)
{
  return boot_malloc(size);
}

static void boot_free(void *ptr)
{
  (void)ptr;
}

static void send_packet(packet_t *packet)
{
  if (write(INSPECT_FD, packet, sizeof(packet_t)) != sizeof(packet_t))
  {
    perror("write");
    exit(1);
  }
}

void *malloc(size_t size)
{
  if (!initialized) init();
  void *ret = orig_malloc(size);
  packet_t packet = { .type = TYPE_MALLOC, .arg1 = size, .arg2 = 0, .ret = (size_t)ret };
  send_packet(&packet);
  return ret;
}

void *calloc(size_t num, size_t size)
{
  if (!initialized) init();
  void *ret = orig_calloc(num, size);
  packet_t packet = { .type = TYPE_CALLOC, .arg1 = num, .arg2 = size, .ret = (size_t)ret };
  send_packet(&packet);
  return ret;
}

void *realloc(void *ptr, size_t size)
{
  if (!initialized) init();
  void *ret = orig_realloc(ptr, size);
  packet_t packet = { .type = TYPE_REALLOC, .arg1 = (size_t)ptr, .arg2 = size, .ret = (size_t)ret };
  send_packet(&packet);
  return ret;
}

void free(void *ptr)
{
  if (!initialized) init();
  orig_free(ptr);
  packet_t packet = { .type = TYPE_FREE, .arg1 = (size_t)ptr, .arg2 = 0, .ret = 0 };
  send_packet(&packet);
}

static void read_leftovers(int fd)
{
  static char tmp[4096];
  int saved_flags = fcntl(fd, F_GETFL, 0);
  fcntl(fd, F_SETFL, saved_flags | O_NONBLOCK);
  while (read(fd, tmp, sizeof(tmp)) > 0);
  fcntl(fd, F_SETFL, saved_flags);
} 

#ifdef FORK_SERVER
static void fork_server(void)
{
  packet_t packet = { .type = TYPE_READY, .arg1 = 0, .arg2 = 0, .ret = 0 };
  send_packet(&packet);
  char buf;
  while (read(SERVER_FD, &buf, 1) == 1)
  {
    pid_t pid = fork();
    if (pid == 0)
    {
      // child
      return;
    }
    else if (pid > 0)
    {
      // parent
      // send pid to runner
      packet.type = TYPE_PID;
      packet.ret = pid;
      if (write(INSPECT_FD, &packet, sizeof(packet)) != sizeof(packet))
      {
        perror("write");
        kill(pid, SIGKILL);
        exit(1);
      }
      // TODO: timeout
      // wait for child
      int status;
      if (waitpid(pid, &status, 0) < 0)
      {
        perror("waitpid");
        exit(1);
      }
      // read leftovers in stdin
      read_leftovers(STDIN_FILENO);
      // send status to runner
      packet.type = TYPE_WAIT;
      packet.ret = status;
      send_packet(&packet);
    }
    else
    {
      // failed
      perror("fork");
      exit(1);
    }
  }
}
#endif

