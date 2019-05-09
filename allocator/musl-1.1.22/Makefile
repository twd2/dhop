OBJS=aligned_alloc.o expand_heap.o malloc.o malloc_usable_size.o memalign.o posix_memalign.o

.PHONY: all
all: malloc.so

malloc.so: $(OBJS)
	gcc -O2 -shared -fPIC -o $@ $^

%.o: %.c atomic.h atomic_arch.h libc.h malloc_impl.h pthread_impl.h
	gcc -O2 -Wall -fno-stack-protector -fPIC -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free -I. -c $< -o $@

.PHONY: clean
clean:
	-rm *.o *.so
