.PHONY: all
all: naive wrapper.so

naive: naive.c
	gcc -Wall naive.c -o naive

wrapper.so: wrapper.c
	gcc -Wall -shared wrapper.c -o wrapper.so -ldl

.PHONY: test
test: all
	LD_PRELOAD=./wrapper.so ./naive

.PHONY: kill
kill:
	-killall python3
	-killall naive

.PHONY: clean
clean:
	-rm naive wrapper.so

