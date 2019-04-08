.PHONY: all
all: naive wrapper.so simplemalloc.so

naive: naive.c
	gcc -O2 -Wall naive.c -o naive

%.so: %.c
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
	-rm naive wrapper.so simplemalloc.so

