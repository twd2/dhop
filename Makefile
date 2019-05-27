LOOP_FINDER=loop-finder/build/loop-finder
TEST_CASES=test/naive test/usermgmt test/switchtest test/switchtest-nopie test/babyheap \
test/bm_0noise_null test/bm_1noise_null test/bm_2noise_null test/bm_4noise_null test/bm_0noise_php-7.2.17 test/bm_1noise_php-7.2.17 test/bm_2noise_php-7.2.17 test/bm_4noise_php-7.2.17 test/bm_0noise_python-3.6.7 test/bm_1noise_python-3.6.7 test/bm_2noise_python-3.6.7 test/bm_4noise_python-3.6.7
ALLOCATORS=allocator/simplemalloc/simplemalloc.so allocator/dlmalloc-2.8.6/malloc.so allocator/tcmalloc-2.7/libtcmalloc.so allocator/jemalloc-5.2.0/libjemalloc.so allocator/uClibc-ng-1.0.31/ucmalloc.so allocator/avr-libc-2.0.0/malloc.so allocator/musl-1.1.22/malloc.so

.PHONY: all
all: wrapper.so wrapper_hook.so $(LOOP_FINDER) $(TEST_CASES) $(ALLOCATORS)

.PHONY: solver
solver: wrapper.so $(TEST_CASES) $(ALLOCATORS)

.PHONY: loop-finder/build/loop-finder
loop-finder/build/loop-finder:
	cd loop-finder && mkdir -p build && cd build && cmake -DCMAKE_BUILD_TYPE=Debug .. && make

test/%: test/%.c
	gcc -O2 -Wall -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free $^ -o $@
	cp $@ $@-stripped && strip $@-stripped

test/switchtest: test/switchtest.c test/foo.o
	gcc -O2 -Wall $^ -o $@
	cp $@ $@-stripped && strip $@-stripped

test/switchtest-nopie: test/switchtest.c test/foo.o
	gcc -fno-PIC -no-pie -O2 -Wall $^ -o $@

test/%.o: test/%.c
	gcc -O2 -Wall -c $^ -o $@

test/%: test/%.prebuilt
	ln -fs $*.prebuilt $@

%.so: %.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -ldl

wrapper.so: wrapper.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -ldl

%.s.o: %.s
	gcc -c $^ -o $@

wrapper_hook.so: wrapper.c hook.s.o
	gcc -DDO_HOOK -O2 -Wall -fno-stack-protector -fPIC -shared $^ -o $@ -lcapstone -ldl

allocator/simplemalloc/simplemalloc.so: allocator/simplemalloc/simplemalloc.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free -shared $^ -o $@ -ldl

allocator/dlmalloc-2.8.6/malloc.so: allocator/dlmalloc-2.8.6/malloc.c
	gcc -O2 -Wall -fno-stack-protector -fPIC -fno-builtin-malloc -fno-builtin-calloc -fno-builtin-realloc -fno-builtin-free -shared $^ -o $@ -ldl

allocator/tcmalloc-2.7/libtcmalloc.so: allocator/tcmalloc-2.7/libtcmalloc.so.prebuilt
	ln -fs libtcmalloc.so.prebuilt $@

allocator/jemalloc-5.2.0/libjemalloc.so: allocator/jemalloc-5.2.0/libjemalloc.so.prebuilt
	ln -fs libjemalloc.so.prebuilt $@

.PHONY: allocator/uClibc-ng-1.0.31/ucmalloc.so
allocator/uClibc-ng-1.0.31/ucmalloc.so:
	cd allocator/uClibc-ng-1.0.31 && make

.PHONY: allocator/avr-libc-2.0.0/malloc.so
allocator/avr-libc-2.0.0/malloc.so:
	cd allocator/avr-libc-2.0.0 && make

.PHONY: allocator/musl-1.1.22/malloc.so
allocator/musl-1.1.22/malloc.so:
	cd allocator/musl-1.1.22 && make

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
	-rm test/*.o *.o *.so allocator/*/*.so allocator/*/*.o
	-cd test && ls | grep -vE '\.(c|prebuilt|py)$$' | xargs rm
	-cd allocator/uClibc-ng-1.0.31 && make clean
	-cd allocator/avr-libc-2.0.0 && make clean
	-cd allocator/musl-1.1.22 && make clean

