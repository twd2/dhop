.PHONY: all
all: loop-finder/build/loop-finder test/naive test/usermgmt test/switchtest test/switchtest-nopie wrapper.so wrapper_hook.so allocator/simplemalloc/simplemalloc.so

.PHONY: loop-finder/build/loop-finder
loop-finder/build/loop-finder:
	cd loop-finder && mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Debug .. && make

test/%: test/%.c
	gcc -O2 -Wall $^ -o $@

test/switchtest: test/switchtest.c test/foo.o
	gcc -O2 -Wall $^ -o $@

test/switchtest-nopie: test/switchtest.c test/foo.o
	gcc -fno-PIC -no-pie -O2 -Wall $^ -o $@

test/%.o: test/%.c
	gcc -O2 -Wall -c $^ -o $@

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
	-rm -r loop-finder/build
	-rm test/naive test/usermgmt test/switchtest test/switchtest-nopie test/*.o *.o *.so allocator/*/*.so

