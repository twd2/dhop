#include <string.h>
#include <unistd.h>

void *malloc(size_t size)
{
  size = (size + 15) & ~15;
  return sbrk(size);
}

void *calloc(size_t num, size_t size)
{
  void *ptr = malloc(num * size);
  memset(ptr, 0, num * size);
  return ptr;
}

void *realloc(void *ptr, size_t size)
{
  return malloc(size);
}

void free(void *ptr)
{
  (void)ptr;
}
