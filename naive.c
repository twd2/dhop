#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define read_ptr(ptr_ptr) scanf("%lx", (uintptr_t *)(ptr_ptr))

int main()
{
  //return 0;
  puts("=== NAIVE MALLOC ===\n"
       "1. malloc\n"
       "2. calloc\n"
       "3. realloc\n"
       "4. free\n"
       "5. exit");
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
      printf("%p\n", malloc(size));
      break;
    case 2:
      printf("size? ");
      if (scanf("%lu", &size) <= 0) return 1;
      printf("%p\n", calloc(1, size));
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

