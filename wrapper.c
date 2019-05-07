#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#ifdef DO_HOOK
// TODO: #include <asm/cachectl.h>
#include <sys/mman.h>

#include <capstone/capstone.h>
#endif // DO_HOOK


#define UNUSED(x) ((void)(x))

#define INSPECT_FD 3
#define SERVER_FD  4
#define FORK_SERVER 1

#define TYPE_READY    0
#define TYPE_PID      1
#define TYPE_MALLOC   2
#define TYPE_CALLOC   3
#define TYPE_REALLOC  4
#define TYPE_FREE     5
#define TYPE_EXIT     6
#define TYPE_MAIN_LOOP 1000
#define TYPE_STDIN    10000
#define TYPE_STDOUT   10001

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
#endif // FORK_SERVER

#ifdef DO_HOOK

#define JMP_SIZE 5 // JMP rel32
#define HIDDEN __attribute__((visibility("hidden")))
#define PAGE_SIZE 0x1000

typedef struct
{
  uint8_t *inst, *hook, *next_inst, *next_hook, *hook_code, *next_hook_code;
  size_t inst_len;
  uint8_t inst_backup[JMP_SIZE], next_inst_backup[JMP_SIZE];
} hook_ctx_t;

typedef struct
{
  uintptr_t r15;
  uintptr_t r14;
  uintptr_t r13;
  uintptr_t r12;
  uintptr_t r11;
  uintptr_t r10;
  uintptr_t r9;
  uintptr_t r8;
  uintptr_t rdi;
  uintptr_t rsi;
  uintptr_t rbp;
  uintptr_t rbx;
  uintptr_t rdx;
  uintptr_t rcx;
  uintptr_t rax;
  uintptr_t rflags;
} regs_t;

typedef void (*hook_func_ptr_t)(hook_ctx_t *ctx, regs_t *);

extern uint8_t asm_code[], asm_code_end[];
extern uint8_t asm_hook_entry[], asm_ctx[], asm_do_hook[], asm_hook_ret[];

static size_t get_inst_length(const uint8_t *code, size_t len, size_t min_len);
static void *mmap_near(void *addr, size_t len, int prot);
static void hook_init(hook_ctx_t *ctx, uint8_t *code, size_t len);
static void hook_set_func(hook_ctx_t *ctx, hook_func_ptr_t func, hook_func_ptr_t next_func);
static void hook_inst(hook_ctx_t *ctx);
static void hook_next_inst(hook_ctx_t *ctx);
static void hook_clear(hook_ctx_t *ctx);
static void hook_die(hook_ctx_t *ctx, regs_t *regs);
static void hook_do_next(hook_ctx_t *ctx, regs_t *regs);

static hook_ctx_t hook_ctx, write_hook_ctx;
static void loop_hook(hook_ctx_t *ctx, regs_t *regs);
static void write_hook(hook_ctx_t *ctx, regs_t *regs);
#endif // DO_HOOK

static char initialized = 0;
static char tmp[1 << 16] = { 0 };
static size_t ptr = 0;

typedef void *(*malloc_ptr_t)(size_t size);
typedef void *(*calloc_ptr_t)(size_t num, size_t size);
typedef void *(*realloc_ptr_t)(void *ptr, size_t size);
typedef void (*free_ptr_t)(void *ptr);

static malloc_ptr_t orig_malloc = boot_malloc;
static calloc_ptr_t orig_calloc = boot_calloc;
static realloc_ptr_t orig_realloc = boot_realloc;
static free_ptr_t orig_free = boot_free;

#ifndef READ
#define READ read
#endif

#ifndef WRITE
#define WRITE write
#endif

static void send_packet(packet_t *packet)
{
  if (WRITE(INSPECT_FD, packet, sizeof(packet_t)) != sizeof(packet_t))
  {
    perror("write");
    exit(1);
  }
}

static void init(void)
{
  initialized = 1;
  setvbuf(stdin, NULL, _IONBF, 0);
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);

#ifdef DO_HOOK
  // Install hooks.
  packet_t packet = { .type = TYPE_READY, .arg1 = 0, .arg2 = 0, .ret = 0 };
  send_packet(&packet);
  uint8_t *code;
  if (READ(SERVER_FD, &code, sizeof(code)) != sizeof(code))
  {
    perror("read");
    exit(1);
  }
  if (code)
  {
    hook_init(&hook_ctx, code, 32);
    hook_set_func(&hook_ctx, loop_hook, hook_do_next);
  }

  void *libc_write = dlsym(RTLD_NEXT, "write");
  hook_init(&write_hook_ctx, libc_write, 32);
  hook_set_func(&write_hook_ctx, write_hook, hook_do_next);
#endif // DO_HOOK

  // Load symbols.
  malloc_ptr_t dl_malloc = dlsym(RTLD_NEXT, "malloc");
  calloc_ptr_t dl_calloc = dlsym(RTLD_NEXT, "calloc");
  realloc_ptr_t dl_realloc = dlsym(RTLD_NEXT, "realloc");
  free_ptr_t dl_free = dlsym(RTLD_NEXT, "free");
  (void)dlsym(RTLD_NEXT, "puts");
  (void)dlsym(RTLD_NEXT, "printf");
  (void)dlsym(RTLD_NEXT, "scanf");
  (void)dlsym(RTLD_NEXT, "fprintf");
  (void)dlsym(RTLD_NEXT, "fscanf");
  (void)dlsym(RTLD_NEXT, "exit");
  // Commit.
  orig_malloc = dl_malloc;
  orig_calloc = dl_calloc;
  orig_realloc = dl_realloc;
  orig_free = dl_free;

#ifdef FORK_SERVER
  fork_server();
#endif // FORK_SERVER
}

static void ctor(void) __attribute__((constructor));
static void ctor(void)
{
  if (!initialized) init();
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
  UNUSED(ptr);
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
  while (READ(fd, tmp, sizeof(tmp)) > 0);
  fcntl(fd, F_SETFL, saved_flags);
}

#ifdef FORK_SERVER
// Fork Server - server side
static void fork_server(void)
{
  packet_t packet = { .type = TYPE_READY, .arg1 = 0, .arg2 = 0, .ret = 0 };
  send_packet(&packet);

  char buf;
  // Wait for a request.
  while (READ(SERVER_FD, &buf, 1) == 1)
  {
    pid_t pid = fork();
    if (pid == 0)
    {
      // child
      // Wait to continue.
      if (READ(SERVER_FD, &buf, 1) != 1)
      {
        perror("read");
        exit(1);
      }
      return;
    }
    else if (pid > 0)
    {
      // parent
      // send pid to runner
      packet.type = TYPE_PID;
      packet.ret = pid;
      if (WRITE(INSPECT_FD, &packet, sizeof(packet)) != sizeof(packet))
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
      packet.type = TYPE_EXIT;
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
#endif // FORK_SERVER

#ifdef DO_HOOK
static size_t get_inst_length(const uint8_t *code, size_t len, size_t min_len)
{
  csh handle;

  if (cs_open(CS_ARCH_X86, CS_MODE_64, &handle) != CS_ERR_OK)
  {
    fprintf(stderr, "cs_open failed.\n");
    exit(1);
  }

  const uint8_t *target_code = code + min_len;
  const uint8_t *current_code = code;
  size_t current_len = len;
  uint64_t current_address = (uint64_t)code;

  cs_insn *insn = cs_malloc(handle);
  while (cs_disasm_iter(handle, &current_code, &current_len, &current_address, insn))
  {
    if (current_code >= target_code)
    {
      break;
    }
  }
  size_t ret = 0;
  if (current_code >= target_code)
  {
    ret = current_code - code;
  }
  cs_free(insn, 1);
  cs_close(&handle);
  if (!ret)
  {
    fprintf(stderr, "get_inst_length failed.\n");
    exit(1);
  }
  return ret;
}

static void *mmap_near(void *addr, size_t len, int prot)
{
  void *expected = (void *)((uintptr_t)addr & ~(PAGE_SIZE - 1));
  while (1)
  {
    void *ret = mmap(expected, len, prot, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (ret == expected)
    {
      break;
    }
    if (ret != MAP_FAILED)
    {
      munmap(ret, len);
    }
    expected = (void *)((uintptr_t)expected - PAGE_SIZE);
  }
  return expected;
}

static void hook_init(hook_ctx_t *ctx, uint8_t *code, size_t len)
{
  const size_t asm_offset_hook_entry = asm_hook_entry - asm_code,
               asm_offset_ctx = asm_ctx - asm_code,
               asm_offset_do_hook = asm_do_hook - asm_code,
               asm_offset_hook_ret = asm_hook_ret - asm_code,
               asm_len = asm_code_end - asm_code;
  UNUSED(asm_offset_do_hook);

  ctx->inst_len = get_inst_length(code, len, JMP_SIZE);
  ctx->inst = code;
  ctx->next_inst = code + ctx->inst_len;
  // Save old instruction bytes.
  memcpy(ctx->inst_backup, ctx->inst, JMP_SIZE);
  memcpy(ctx->next_inst_backup, ctx->next_inst, JMP_SIZE);

  ctx->hook_code = mmap_near(ctx->inst, PAGE_SIZE, PROT_READ | PROT_WRITE);
  // Copy hook code.
  memcpy(ctx->hook_code, asm_code, asm_len);
  // Do relocate.
  *(uint64_t *)(ctx->hook_code + asm_offset_ctx) = (uint64_t)ctx;
  *(int32_t *)(ctx->hook_code + asm_offset_hook_ret) +=
      (uintptr_t)ctx->inst - ((uintptr_t)ctx->hook_code + asm_offset_hook_ret);
  ctx->hook = ctx->hook_code + asm_offset_hook_entry;
  hook_inst(ctx);

  // For the next hook.
  ctx->next_hook_code = ctx->hook_code + ((asm_len + 15) & ~15); // do not mmap a new page
  // Copy hook code.
  memcpy(ctx->next_hook_code, asm_code, asm_len);
  // Do relocate.
  *(uint64_t *)(ctx->next_hook_code + asm_offset_ctx) = (uint64_t)ctx;
  *(int32_t *)(ctx->next_hook_code + asm_offset_hook_ret) +=
      (uintptr_t)ctx->next_inst - ((uintptr_t)ctx->next_hook_code + asm_offset_hook_ret);
  ctx->next_hook = ctx->next_hook_code + asm_offset_hook_entry;
  mprotect(ctx->hook_code, PAGE_SIZE, PROT_READ | PROT_EXEC);
  hook_set_func(ctx, hook_die, hook_die);
}

static void hook_set_func(hook_ctx_t *ctx, hook_func_ptr_t func, hook_func_ptr_t next_func)
{
  const size_t asm_offset_do_hook = asm_do_hook - asm_code;
  mprotect(ctx->hook_code, PAGE_SIZE, PROT_READ | PROT_WRITE);
  *(uint64_t *)(ctx->hook_code + asm_offset_do_hook) = (uint64_t)func;
  *(uint64_t *)(ctx->next_hook_code + asm_offset_do_hook) = (uint64_t)next_func;
  mprotect(ctx->hook_code, PAGE_SIZE, PROT_READ | PROT_EXEC);
}

#define HOOK_PROLOGUE() \
do \
{ \
  mprotect((void *)((uintptr_t)ctx->inst & ~(PAGE_SIZE - 1)), \
           ((uintptr_t)ctx->inst & (PAGE_SIZE - 1)) + ctx->inst_len + JMP_SIZE, \
           PROT_READ | PROT_WRITE); \
} while (0)

#define HOOK_EPILOGUE() \
do \
{ \
  mprotect((void *)((uintptr_t)ctx->inst & ~(PAGE_SIZE - 1)), \
           ((uintptr_t)ctx->inst & (PAGE_SIZE - 1)) + ctx->inst_len + JMP_SIZE, \
           PROT_READ | PROT_EXEC); \
} while (0)
// TODO: cacheflush(ctx->inst, ctx->inst_len + JMP_SIZE, ICACHE);

static void hook_inst(hook_ctx_t *ctx)
{
  HOOK_PROLOGUE();
  // jmp to hook entry
  *ctx->inst = 0xe9;
  // Do relocate.
  *(int32_t *)(ctx->inst + 1) =
      (int32_t)((uintptr_t)ctx->hook - ((uintptr_t)ctx->inst + JMP_SIZE));
  // Uninstall other hooks.
  memcpy(ctx->next_inst, ctx->next_inst_backup, JMP_SIZE);
  HOOK_EPILOGUE();
}

static void hook_next_inst(hook_ctx_t *ctx)
{
  HOOK_PROLOGUE();
  // jmp to hook entry
  *ctx->next_inst = 0xe9;
  // Do relocate.
  *(int32_t *)(ctx->next_inst + 1) =
      (int32_t)((uintptr_t)ctx->next_hook - ((uintptr_t)ctx->next_inst + JMP_SIZE));
  // Uninstall other hooks.
  memcpy(ctx->inst, ctx->inst_backup, JMP_SIZE);
  HOOK_EPILOGUE();
}

static void hook_clear(hook_ctx_t *ctx)
{
  HOOK_PROLOGUE();
  // Uninstall hooks.
  memcpy(ctx->inst, ctx->inst_backup, JMP_SIZE);
  memcpy(ctx->next_inst, ctx->next_inst_backup, JMP_SIZE);
  HOOK_EPILOGUE();
}

static void hook_die(hook_ctx_t *ctx, regs_t *regs)
{
  UNUSED(regs);
  hook_clear(ctx);
  puts("[ERROR] Hook function not set!");
  for (;;);
}

static void hook_do_next(hook_ctx_t *ctx, regs_t *regs)
{
  UNUSED(regs);
  hook_inst(ctx);
}

static void loop_hook(hook_ctx_t *ctx, regs_t *regs)
{
  UNUSED(regs);
  // puts("[HOOK] The main loop iterates.");
  packet_t packet = { .type = TYPE_MAIN_LOOP, .arg1 = 0, .arg2 = 0, .ret = 0 };
  send_packet(&packet);
  hook_next_inst(ctx);
}

static void write_hook(hook_ctx_t *ctx, regs_t *regs)
{
  hook_clear(ctx); // Uninstall the hook, because we are going to use write().
  int fd = (int)regs->rdi;
  void *buf = (void *)regs->rsi;
  size_t len = (size_t)regs->rdx;
  UNUSED(buf);
  if (fd == STDOUT_FILENO || fd == STDERR_FILENO)
  {
    packet_t packet = { .type = TYPE_STDOUT, .arg1 = len, .arg2 = 0, .ret = 0 };
    send_packet(&packet);
  }
  hook_next_inst(ctx);
}
#endif // DO_HOOK
