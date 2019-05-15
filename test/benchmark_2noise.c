#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define read_ptr(ptr_ptr) scanf("%lx", (uintptr_t *)(ptr_ptr))

void make_trace();

int main()
{
  setvbuf(stdin, NULL, _IONBF, 0);
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);
  make_trace();
  int op;
  size_t size;
  void *ptr;
  while (1)
  {
    printf("op? ");
    if (scanf("%d", &op) <= 0) return 1;
    switch (op)
    {
    case 1:
      printf("size? ");
      if (scanf("%lu", &size) <= 0) return 1;
      ptr = malloc(size);
      *(void **)ptr = malloc(8);
      *((void **)ptr + 1) = malloc(32);
      printf("%p\n", ptr);
      break;
    case 2:
      printf("size? ");
      if (scanf("%lu", &size) <= 0) return 1;
      ptr = calloc(1, size);
      *(void **)ptr = malloc(8);
      *((void **)ptr + 1) = malloc(32);
      printf("%p\n", ptr);
      break;
    case 3:
      printf("ptr? ");
      if (read_ptr(&ptr) <= 0) return 1;
      printf("size? ");
      if (scanf("%lu", &size) <= 0) return 1;
      printf("%p\n", realloc(ptr, size));
      break;
    case 4:
      printf("ptr? ");
      if (read_ptr(&ptr) <= 0) return 1;
      free(*(void **)ptr);
      free(*((void **)ptr + 1));
      free(ptr);
      break;
    case 5:
      return 0;
    default:
      return 1;
    }
  }
  return 0;
}

