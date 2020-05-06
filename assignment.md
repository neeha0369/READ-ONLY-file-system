Programming Assignment 3 - read-mostly file system
------------------------------------------------

In this assignment you will implement a mostly-read-only version of a Unix-like file system using the FUSE library.

Assignment Details
------------------

**Materials:** You will be provided with the following materials in your team repository:

- Makefile
- fs5600.h - structure definitions
- homework.c - skeleton code
- misc.c, hw3fuse.c - support code 
- libhw3.c, hw3test.py - python-based unit test framework
- gen-disk.py, disk1.in - generates file system image
- valgrind-python.supp - see testing section for details

**Deliverables:** You will be using the FUSE library, which is based on the VFS interface, and will need to implement the following methods:

- `getattr` - get attributes of a file/directory
- `readdir` - enumerate entries in a directory
- `read` - read data from a file
- `rename` - rename a file (only within the same directory)
- `chmod` - change file permissions
- `statfs` - report file system statistics
- `init` - constructor (i.e. put your init code here)

Your code will run under two different frameworks - a python-based test framework which will be used for unit testing, and the FUSE library which will run your code as a real file system. In each case your code will read blocks from a “disk” (actually an image file) using the `block_read` function.

Note that your code will **not** use standard file system functions like `open`, `read`, `stat`, `readdir` etc. - your code is responsible for files and directories which are encoded in the data blocks which you access via `block_read` and `block_write`. 

You will be graded on the following code in your repository:

- `homework.c` - implementation
- `tests.py` - unit tests

File System Definition
======================

The file system uses a 4KB block size; it is simplified from the classic Unix file system by (a) using full blocks for inodes, and (b) putting all block pointers in the inode. This results in the following differences:

1. There is no need for a separate inode region or inode bitmap – an inode is just another block, marked off in the block bitmap
2. Limited file size – a 4KB inode can hold 1018 32-bit block pointers, for a max file size of about 4MB
3. Disk size – a single 4KB block (block 1) is reserved for the block bitmap; since this holds 32K bits, the biggest disk image is 32K * 4KB = 128MB

Although the file size and disk size limits would be serious problems in practice, they won't be any trouble for the assignment since you'll be dealing with disk sizes of 1MB or less.

File System Format
------------------
The disk is divided into blocks of 4096 bytes, and into 3 regions: the superblock, the block bitmap, and file/inode blocks, with the first file/inode block (block 2) always holding the root directory.

```
	  +-------+--------+----------+------------------------+
	  | super | block  | root dir |     data blocks ...    |
	  | block | bitmap |   inode  |                        |
	  +-------+--------+----------+------------------------+
    block     0        1         2          3 ...
```

**Superblock:**
The superblock is the first block in the file system, and contains the  information needed to find the rest of the file system structures. 
The following C structure (found in `fs5600.h`) defines the superblock:
```
    struct fsx_superblock {
	uint32_t magic;             /* 0x37363030 */
	uint32_t disk_size;         /* in 4096-byte blocks */
	char pad[4088];             /* to make size = 4096 */
    };
```
Note that `uint32_t` is a standard C type found in the `<stdint.h>` header file, and refers to an unsigned 32-bit integer. (similarly, `uint16_t`, `int16_t` and `int32_t` are unsigned/signed 16-bit ints and signed 32-bit ints)

**Inodes:**
Inodes
These are based on the standard Unix-style inode; however they're bigger and have no indirect block pointers. Each inode corresponds to a file or directory; in a sense the inode is that file or directory, which can be uniquely identified by its inode number, which is just its block number. The root directory is always found in inode 2; inode 0 is invalid and can be used as a 'null' value.
```
struct fs_inode {
    uint16_t uid;      /* file owner */
    uint16_t gid;      /* group */
    uint32_t mode;     /* type + permissions (see below) */
    uint32_t ctime;    /* creation time */
    uint32_t mtime;    /* modification time */
    int32_t  size;     /* size in bytes */
    uint32_t ptrs[FS_BLOCK_SIZE/4 - 5]; /* inode = 4096 bytes */
};
```

**"Mode":**
The FUSE API (and Linux internals in general) mash together the concept of object type (file/directory/device/symlink...) and permissions. The result is called the file "mode", and looks like this:
```
        |<-- S_IFMT --->|           |<-- user ->|<- group ->|<- world ->|
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
        | F | D |   |   |   |   |   | R | W | X | R | W | X | R | W | X |
        +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
```
Since it has multiple 3-bit fields, it is commonly displayed in base 8 (octal) - e.g. permissions allowing RWX for everyone (rwxrwxrwx) are encoded as '777'. (Hint - in Python, which you'll be using for testing, octal numbers are indicated with "0o", e.g. 0o777) The F and D bits correspond to 0o100000 and 0o40000.

 which (at least since the demise of 36-bit computers in the early 70s) is about the only thing in the world that octal is useful for.

**Directories:**
Directories are a multiple of one block in length, holding an array of directory entries:
```
    struct fs_dirent {
	uint32_t valid : 1;
	uint32_t inode : 31;
	char name[28];       /* with trailing NUL */
    };
```
Each "dirent" is 32 bytes, giving 4096/32 = 128 directory entries in each block. The directory size in the inode is always a multiple of 4096, and unused directory entries are indicated by setting the 'valid' flag to zero. The maximum name length is 27 bytes, allowing entries to always have a terminating 0 byte so you can use `strcmp` etc. without any complications.

**Storage allocation:**
Since you won't be creating or deleting files and directories, you don't have to worry about the block bitmap for anything other than calculating free space. For this you're given the following function:
```
bit_test((void*)map, int i);
```
If you allocate a character array of 4096 bytes and read block 1 into it, you can pass it to the `bit_test` function.

Implementation advice
---------------------

It's fine to assume a maximum depth for subdirectories, e.g. 10 in the example below.

Note that FUSE declares the `path` argument to all your methods as "const char *", not "char *", which is really annoying. It means that you need to copy the path before you can split it using `strtok`, typically using the `strdup` function. E.g.:

```
    int fs_xyz(const char *c_path, ...)
    {
	char *path = strdup(c_path);
	/* do stuff with 'path' */
	free(path);
    }
```

The first thing you're probably going to have to do with that path is to split it into components - here's some code to do that, using the `strtok` library function:
```
    #define MAX_PATH_LEN 10
    #define MAX_NAME_LEN 27
    int parse(char *path, char **argv)
    {
        int i;
        for (i = 0; i < MAX_PATH_LEN; i++) {
            if ((argv[i] = strtok(path, "/")) == NULL)
                break;
            if (strlen(argv[i]) > MAX_NAME_LEN)
                argv[i][MAX_NAME_LEN] = 0;        // truncate to 27 characters
            path = NULL;
        }
        return i;
    }
```

**Translating path to inode:**
PLEASE factor out the code that you use for translating paths into inodes. Nothing good can come of duplicating the same code in every one of your functions.

I would suggest factoring out a function which translates a path in count,array form into an inode number. That way you can return an error (negative integer) if it's not found, and accessing the inode itself is just a matter of reading that block number into a `struct fs_inode`. Note that accessing the parent directory is easy using count/array format - it's just (count-1)/array.

**Efficiency**
Don't worry about efficiency. In the straightforward implementation, evey single operation will read every single directory from the root down to the file being accessed. That's OK.

Testing and Debugging Project 3
===============================

To test your implementation you'll use a pre-made disk image in your repository, `test1.img`. The following instructions describe how to use two different interfaces to your code - a simple Python-based method implemented in `libhw3.c` and `hw3test.py`, and the FUSE interface which allows running it as a real Linux file system, accessible to any application.

Running `make` will build both of these interfaces - the Python interface in `libhw3.so`, and the FUSE executable in `hw3fuse`. It will also generate the `test.img` file that you will use in your tests. (the Makefile regenerates it each time you make anything, in case your code corrupted it) Finally, running `make clean` will delete object files and executables.

Using hw3test.py
----------------

First, import it into python. Here we're renaming it to 'hw3', so we don't have to type 'hw3test' a zillion times:

        import hw3test as hw3

Then initialize it with the name of the image file, `test.img`.

        hw3.init('test.img')

File type constants - the following constants are described in 'man 2 stat' (along with a lot of others that we don't use):

* `hw3.S_IFMT`
* `hw3.S_IFREG`
* `hw3.S_IFDIR`

Error number constants - note that the comments in homework.c will tell you which errors are legal to return from which methods.

* hw3.EPERM - permission error
* hw3.ENOENT - file/dir not found
* hw3.EIO - if `block_read` or `block_write` fail
* hw3.ENOMEM  - out of memory
* hw3.ENOTDIR - what it says
* hw3.EISDIR - what it says
* hw3.EINVAL - invalid parameter (see comments in homework.c)
* hw3.ENOSPC - out of space on disk
* hw3.EOPNOTSUPP - not finished with the homework yet
* hw3.errors[] - maps error code to string (e.g. "if err < 0: print hw3.errors[-err]")

Verbose flag:

* hw3.verbose - set this to True and each method will print out arguments and return values

Get file attributes:

        sb = getattr(path)

Returns a structure with the following fields (see 'man 2 stat')

 * `sb.st_mode` - file mode (`S_IFREG` or `S_IFDIR`, ORed with 9-bit permissions)
 * `sb.st_uid`, `sb.st_gid` - file owner, file group
 * `sb.st_size` - size in bytes
 * `sb.st_mtime`, `sb.st_ctime` - modification time, creation time

Read from a file:

        val,data = hw3.read(path, len, offset)

Reads up to 'len' bytes starting at 'offset'. 'val' is the number of bytes read, or <0 in the case of errors

List a directory:

        val, entries = hw3.readdir(path)

Returns: 'val' is 0 or negative (error code), and 'entries' is an array of structures with the following fields. (all but 'name' are the same as for 'getattr')

 * `entries[i].name`
 * `entries[i].st_mode`
 * `entries[i].st_uid`, `st_gid`
 * `entries[i].st_size`
 * `entries[i].st_mtime`, `st_ctime`

Get file system attributes:

        val,sv = hw3.statvfs()

Returns: val - 0 for success, negative for error, sv has the following fields:
 * `sv.f_bsize` - 4096
 * `sv.f_blocks` - total number of blocks (1024 for test image)
 * `sv.f_bfree` - free blocks (731 for test image)
 * `sv.f_namemax` - 27

Change filename:

        val = hw3.rename(path1, path2)

Returns: 0 for success, negative for error.

Change permissions:

       val = hw3.chmod(path, mode)

Returns: 0 for success, negative for error. 'mode' is an integer, and should encode valid Unix permissions. (i.e. only the bottom 9 bits should be set, giving a value between 0 and octal 777) As a reminder, you can specify octal numbers in Python with an '0o' prefix, e.g. 0o777.

Finally, if you set the flag `hw3.verbose` to `True` it will print out all the arguments and return values to the functions you call:

```
    >>> hw3.verbose = True
    >>> hw3.getattr('/')
    getattr(/) = 0 (st_mode=40777 st_uid=0 st_size=4096 st_mtime=1565283167)
    (0, <hw3test.stat object at 0x7f999ccbd560>)
```


Using the Python interface directly
-----------------------------------

You can use the interface directly, as follows:

```
    hw3$ python
    Python 2.7.15+ (default, Oct  7 2019, 17:39:04) 
    [GCC 7.4.0] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import hw3test as hw3
    >>> hw3.init('test.img')
    0
    >>> hw3.readdir('/')
    (0, [<hw3test.dirent object at 0x7fdebf733e60>, <hw3test.dirent object at 0x7fdebf733f80>, <hw3test.dirent object at 0x7fdebf6af050>, <hw3test.dirent object at 0x7fdebf6af0e0>, <hw3test.dirent object at 0x7fdebf6af170>, <hw3test.dirent object at 0x7fdebf6af200>, <hw3test.dirent object at 0x7fdebf6af290>])
    >>> [x.name for x in _[1]]
    ['file.1k', 'file.10', 'dir-with-long-name', 'dir2', 'dir3', 'file.12k+', 'file.8k+']
    >>> hw3.read('file.1k', 40, 0)
    (40, 'RfmJatlKvcpvbFMfyXtpwGkjQmVtVepOIFhXoOUn')
    >>> 
```

However you'll probably be using it mostly for writing tests.


Using Python unittest
---------------------

For testing we will use the Python [unittest](https://docs.python.org/2/library/unittest.html) framework. To use it:

1. Import 'unittest',
2. create a class that subclasses `unittest.TestCase`
3. define methods for that class with names starting with 'test'.
4. Verify results using `self.assertTrue(expression)` or one of the other [test asserts](https://docs.python.org/2/library/unittest.html#assert-methods) provided by the library.

An example:

    #!/usr/bin/python
    import unittest
    import hw3test as hw3

    class tests(unittest.TestCase):
        def test_1_succeeds(self):
            print 'Test 1 - always succeeds'
            self.assertTrue(True)

        def test_2_fails(self):
            print 'test 2 - always fails'
            self.assertTrue(False)

    if __name__ == '__main__':
        hw3.init('test.img')
        unittest.main()

If you don't know python, [here's](https://stackoverflow.com/questions/8228257/what-does-if-name-main-mean-in-python) an explanation of the last three lines. 

Once you've implemented it you can create a simple test to see if it works, since the return values for the mktest image are known values:

    def test_1_statfs(self):
        print 'Test 1 - statfs:'
        v,sfs = hw3.statfs()
        self.assertTrue(v == 0)
        self.assertTrue(sfs.f_bsize == 4096)    # defined in fs5600.h
        self.assertTrue(sfs.f_blocks == 398)    # test.img - 400 blocks - super - bitmap
        self.assertTrue(sfs.f_bfree == 355)     # test.img
        self.assertTrue(sfs.f_namemax == 27)    # again from FS definition

Now you can run your test script; hopefully the results will be boring like this:
    hw3$ python test-q1.py 
    Test 1 - statfs:
    .
    ----------------------------------------------------------------------
    Ran 1 test in 0.001s

    OK
    hw3$

If you want to run only a single test, you can specify that test on the command line 
by giving its class and method name:

    hw3$ python test-q1b.py tests.test_1_statfs
    Test 1 - statfs:
    .
    ----------------------------------------------------------------------
    Ran 1 test in 0.000s

    OK
    hw3$ 

Debugging
---------

In a perfect world you would write your code, writing your tests as you go along, and the tests would never fail or crash. Things don't work that way:

    hw3$ python test-q1.py
    Test 1 - statfs:
    Segmentation fault (core dumped)
    hw3$ 

It's not immediately obvious how to debug your code when this happens - what you need to do is to run python under GDB:
    hw3$ gdb --args python test-q1b.py 
    GNU gdb (Ubuntu 7.11.1-0ubuntu1~16.5) 7.11.1
     [yada, yada...]
    Reading symbols from python...(no debugging symbols found)...done.
    (gdb) run
    Starting program: /usr/bin/python test-q1b.py
    [Thread debugging using libthread_db enabled]
    Using host libthread_db library "/lib/i386-linux-gnu/libthread_db.so.1".
    Test 1 - statfs:

    Program received signal SIGSEGV, Segmentation fault.
    0xb7fca234 in fs_statfs (path=0xb7d33634 "/", st=0x8478ab0)
        at homework-soln.c:936
    936     *(char*)0 = 0; /* crash to demonstrate debugging */
    (gdb) 

But what if you want to set a breakpoint? Just set it before typing 'run' in Gdb, and it should work:
    hw3$ gdb --args python test-q1b.py 
    GNU gdb (Ubuntu 7.11.1-0ubuntu1~16.5) 7.11.1
      [...]
    Reading symbols from python...(no debugging symbols found)...done.
    (gdb) b fs_statfs
    Function "fs_statfs" not defined.
    Make breakpoint pending on future shared library load? (y or [n]) y
    Breakpoint 1 (fs_statfs) pending.
    (gdb) run
    Starting program: /usr/bin/python test-q1b.py
    [Thread debugging using libthread_db enabled]
    Using host libthread_db library "/lib/i386-linux-gnu/libthread_db.so.1".
    Test 1 - statfs:

    Breakpoint 1, fs_statfs (path=0xb7d33634 "/", st=0x8478ab0)
        at homework.c:936
    936     *(char*)0 = 0; /* crash to demonstrate debugging */
    (gdb)  

As part of your debugging I would advise running the `valgrind` utility. First you'll need to install it:

    hw3$ sudo apt install valgrind
    [sudo] password for pjd: 
    Reading package lists... Done
    Building dependency tree       
     ...
    hw3$

Then you can run your program with valgrind:

    hw3$ valgrind python test-q1.py 
    ==21854== Memcheck, a memory error detector
    ==21854== Copyright (C) 2002-2017, and GNU GPL'd, by Julian Seward et al.
    ==21854== Using Valgrind-3.13.0 and LibVEX; rerun with -h for copyright info
    ==21854== Command: python test-q1.py
    ==21854== 
    ==21854== Invalid read of size 4
    ==21854==    at 0x157C0F: PyObject_Free (in /usr/bin/python2.7)
    ==21854==    by 0x1EA575: ??? (in /usr/bin/python2.7)
    ==21854==    by 0x210FCA: ??? (in /usr/bin/python2.7)

and discover that valgrind **really** doesn't like Python. You'll need to use the included valgrind init file:

    hw3$ valgrind --suppressions=valgrind-python.supp python test.py 
    ==21939== Memcheck, a memory error detector
    ==21939== Copyright (C) 2002-2017, and GNU GPL'd, by Julian Seward et al.
    ==21939== Using Valgrind-3.13.0 and LibVEX; rerun with -h for copyright info
    ==21939== Command: python test-q1.py
    ==21939== 
       ...
    ==21939== 
    ==21939== For counts of detected and suppressed errors, rerun with: -v
    ==21939== ERROR SUMMARY: 0 errors from 0 contexts (suppressed: 6185 from 92)
    
Contents of test.img
--------------------

If you build and run the `hw3fuse` executable you can run it with the following command:

    ./hw3fuse -image test.img [dir]

and (assuming it doesn't crash) it will mount the file system in test.img on top of the specified directory and run in the background, letting us see the contents:

```
    hw3$ mkdir dir
    hw3$ ./hw3fuse -image test.img dir
    hw3$ ls dir
    dir2  dir3  dir-with-long-name  file.10  file.12k+  file.1k  file.8k+
    hw3$ ls -l dir
    total 7
    drwxrwxrwx 1  500  500  8192 Aug  8 12:52 dir2
    drwxrwxrwx 1 root  500  4096 Aug  8 12:52 dir3
    drwxrwxrwx 1 root root  4096 Aug  8 12:52 dir-with-long-name
    -rw-rw-rw- 1  500  500    10 Aug  8 12:52 file.10
    -rw-rw-rw- 1 root  500 12289 Aug  8 12:52 file.12k+
    -rw-rw-rw- 1  500  500  1000 Aug  8 12:52 file.1k
    -rw-rw-rw- 1  500  500  8195 Aug  8 12:52 file.8k+
    hw3$ cd dir
    hw3/dir$ ls -l dir2
    total 2
    -rwxrwxrwx 1 500 500 4098 Aug  8 12:52 file.4k+
    -rw-rw-rw- 1 500 500 1000 Aug  8 12:52 twenty-seven-byte-file-name
    hw3/dir$
```

For your Python test scripts, here's a table of the files and directories, sizes, mtime and ctime values, mode (as returned in `struct stat` - i.e. including S_IFREG or S_IFDIR):

    # path uid gid mode size ctime mtime
    files_dirs =(('/', 0, 0, 0o40777, 4096, 1565283152, 1565283167),
		     ('/file.1k', 500, 500, 0o100666, 1000, 1565283152, 1565283152),
		     ('/file.10', 500, 500, 0o100666, 10, 1565283152, 1565283167),
		     ('/dir-with-long-name', 0, 0, 0o40777, 4096, 1565283152, 1565283167),
		     ('/dir-with-long-name/file.12k+', 0, 500, 0o100666, 12289, 1565283152, 1565283167),
		     ('/dir2', 500, 500, 0o40777, 8192, 1565283152, 1565283167),
		     ('/dir2/twenty-seven-byte-file-name', 500, 500, 0o100666, 1000, 1565283152, 1565283167),
		     ('/dir2/file.4k+', 500, 500, 0o100777, 4098, 1565283152, 1565283167),
		     ('/dir3', 0, 500, 0o40777, 4096, 1565283152, 1565283167),
		     ('/dir3/subdir', 0, 500, 0o40777, 4096, 1565283152, 1565283167),
		     ('/dir3/subdir/file.4k-', 500, 500, 0o100666, 4095, 1565283152, 1565283167),
		     ('/dir3/subdir/file.8k-', 500, 500, 0o100666, 8190, 1565283152, 1565283167),
		     ('/dir3/subdir/file.12k', 500, 500, 0o100666, 12288, 1565283152, 1565283167),
		     ('/dir3/file.12k-', 0, 500, 0o100777, 12287, 1565283152, 1565283167),
		     ('/file.12k+', 0, 500, 0o100666, 12289, 1565283152, 1565283167),
		     ('/file.8k+', 500, 500, 0o100666, 8195, 1565283152, 1565283167))

    
