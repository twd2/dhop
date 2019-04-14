.PHONY: all
all: test/naive wrapper.so wrapper_hook.so allocator/simplemalloc/simplemalloc.so

test/%: test/%.c
	gcc -O2 -Wall $^ -o $@

%.so: %.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -ldl

wrapper.so: wrapper.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -ldl

%.s.o: %.s
	gcc -c $^ -o $@

wrapper_hook.so: wrapper.c hook.s.o
	gcc -DDO_HOOK -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -lcapstone -ldl

allocator/simplemalloc/simplemalloc.so: allocator/simplemalloc/simplemalloc.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -ldl

.PHONY: test
test: all
	LD_PRELOAD=./wrapper.so ./naive

.PHONY: kill
kill:
	-killall python3
	-killall naive

.PHONY: clean
clean:
	-rm test/naive *.o *.so allocator/*/*.so

