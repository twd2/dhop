OBJS=calloc.o free.o heap_alloc.o heap_alloc_at.o heap_free.o malloc.o memalign.o realloc.o

.PHONY: all
all: ucmalloc.so

ucmalloc.so: $(OBJS)
	gcc -O2 -shared -fPIC -o $@ $^

%.o: %.c heap.h malloc.h twd2_patch.h
	gcc -O2 -Wall -fno-stack-protector -fPIC -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free -I. -D__ARCH_USE_MMU__ -c $< -o $@

.PHONY: clean
clean:
	-rm *.o *.so
