OBJS=calloc.o malloc.o realloc.o

.PHONY: all
all: malloc.so

malloc.so: $(OBJS)
	gcc -O2 -shared -fPIC -o $@ $^

%.o: %.c sectionname.h stdlib_private.h
	gcc -O2 -Wall -fno-stack-protector -fPIC -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free -I. -D__AVR__ -c $< -o $@

.PHONY: clean
clean:
	-rm *.o *.so
