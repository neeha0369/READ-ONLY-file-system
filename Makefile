#
# file:        Makefile - programming assignment 3
#

HW = homework.c
CFLAGS = -ggdb3 -Wall
SOFLAGS = -shared -fPIC 
ifdef COVERAGE
CFLAGS += -fprofile-arcs -ftest-coverage
LD_LIBS = --coverage
endif

# note that implicit make rules work fine for compiling x.c -> x
# (e.g. for mktest). Also, the first target defined in the file gets
# compiled if you run without an argument.
#
all: hw3fuse libhw3.so test.img

# force test.img to be rebuilt each time
.PHONY: test.img

# '$^' expands to all the dependencies (i.e. misc.o homework.o image.o)
# and $@ expands to 'homework' (i.e. the target)
#
libhw3.so: libhw3.c $(HW) misc.c
	gcc libhw3.c $(HW) misc.c -o libhw3.so $(CFLAGS) $(SOFLAGS) $(LD_LIBS)

hw3fuse: misc.o $(HW:.c=.o) hw3fuse.o
	gcc -ggdb3 $^ -o $@ -lfuse $(LD_LIBS)

test.img: 
	python gen-disk.py -q disk1.in test.img

clean: 
	rm -f *.o *.so hw3fuse *.gcda *.gcno *.gcov
