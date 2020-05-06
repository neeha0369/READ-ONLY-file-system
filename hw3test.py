#
# tested on: libc6-dev:amd64 2.27-3ubuntu1
# compiled with FUSE_USE_VERSION=27
#               _FILE_OFFSET_BITS=64
#

from ctypes import *
#from enum import IntEnum
import os, sys, random

verbose = False

# 'struct stat' when compiled with _FILE_OFFSET_BITS=64
#
class stat(Structure):
    _fields_ = [("_pad1", c_char * 24),
                ("st_mode", c_uint),      # 24
                ("st_uid", c_uint),       # 28
                ("st_gid", c_uint),       # 32
                ("_pad3", c_char * 12),   # 36
                ("st_size", c_ulonglong), # 48
                ("_pad4", c_char * 32),   # 56
                ("st_mtime", c_ulonglong),# 88
                ("_pad5", c_char * 8),    # 96
                ("st_ctime", c_ulonglong),# 104
                ("_pad6", c_char * 32)]   # 112 -> 144
    def __str__(self):
        return ('st_mode=%o st_uid=%d st_size=%d st_mtime=%d' %
                    (self.st_mode, self.st_uid, self.st_size, self.st_mtime))
    
# used by the readdir function - name plus stat buf
class dirent(Structure):
    _fields_ = [("name", c_char * 64),    # 0
                ("_pad1", c_char * 24),   # 64
                ("st_mode", c_uint),      # 88
                ("st_uid", c_uint),       # 92
                ("st_gid", c_uint),       # 96
                ("_pad3", c_char * 12),   # 100
                ("st_size", c_ulonglong), # 112
                ("_pad4", c_char * 32),   # 120
                ("st_mtime", c_ulonglong), # 152
                ("_pad5", c_char * 8),     #
                ("st_ctime", c_ulonglong), # 168 
                ("_pad6", c_char * 32)]    # 176 -> 208

    def __str__(self):
        return ('name=%s st_mode=%o st_uid=%d st_size=%d st_mtime=%d' %
                (self.name, self.st_mode, self.st_uid, self.st_size, self.st_mtime))

class statvfs(Structure):
    _fields_ = [("f_bsize", c_longlong),  # 0
                ("_pad1", c_char * 8),    # 8
                ("f_blocks", c_longlong), # 16
                ("f_bfree", c_longlong),  # 24
                ("f_bavail", c_longlong), # 32
                ("_pad2", c_char * 40),   # 40
                ("f_namemax", c_longlong),# 80
                ("_pad2", c_char * 24)]   # 88 -> 112
    def __str__(self):
        return ('size=%d blocks=%d bfree=%d namemax=%d' %
                    (self.f_bsize, self.f_blocks, self.f_bfree, self.f_namemax))
    
class fuse_file_info(Structure):
    _fields_ = [("flags", c_int),         # 0
                ("_pad1", c_char * 20),   # 4
                ("fh", c_ulonglong),      # 24
                ("_pad2", c_char * 8)]    # 32 -> 40

class fuse_context(Structure):
    _fields_ = [("_fuse", c_longlong),    # 0
                ("uid", c_uint),          # 8
                ("gid", c_uint),          # 12
                ("pid", c_uint),          # 16
                ("_private", c_char * 8), # 20
                ("_umask", c_uint),       # 28
                ("_pad", c_char * 8)]     # 32 -> 40

        
dir = os.getcwd()
hw3lib = CDLL(dir + "/libhw3.so")

assert hw3lib

ctx = hw3lib.ctx

null_fi = fuse_context()

# python3 - bytes(path) -> bytes(path, 'UTF-8')
#
def xbytes(path):
    if sys.version_info > (3,0):
        return bytes(path, 'UTF-8')
    else:
        return bytes(path)

def init(image):
    return hw3lib.hw3_init(xbytes(image))

def getattr(path):
    sb = stat()
    retval = hw3lib.hw3_getattr(xbytes(path), byref(sb))
    if verbose:
        print ('getattr(%s) = %d (%s)' %
                   (path, retval, strerr(retval) if retval < 0 else str(sb)))
    return retval, sb

dir_max = 128
def readdir(path):
    des = (dirent * dir_max)()
    n = c_int(dir_max)
    val = hw3lib.hw3_readdir(xbytes(path), byref(n), byref(des), byref(null_fi))
    if val >= 0:
        if verbose:
            print('readdir(%s) = [%s]' % (path, ' '.join([str(de.name) for de in des[0:n.value]])))
        return val, des[0:n.value]
    else:
        if verbose:
            print('readdir(%s) = %d (%s)' % (path, val, strerr(val)))
        return val, []
    
def create(path, mode):
    retval = hw3lib.hw3_create(path, c_int(mode), byref(null_fi))
    if verbose:
        print('create(%s,%o) = %d' % (path, mode, retval))
    return retval

def mkdir(path, mode):
    retval = hw3lib.hw3_mkdir(path, c_int(mode))
    if verbose:
        print('mkdir(%s,%o) = %d' % (path, mode, retval))
    return retval

def truncate(path, offset):
    retval = hw3lib.hw3_truncate(path, c_int(offset))
    if verbose:
        print('truncate(%s,%d) = %d' % (path, offset, retval))
    return retval

def unlink(path):
    retval = hw3lib.hw3_unlink(path)
    if verbose:
        print('unlink(%s) = %d' % (path, retval))
    return retval

def rmdir(path):
    retval = hw3lib.hw3_rmdir(path)
    if verbose:
        print('rmdir(%s) = %d' % (path, retval))
    return retval

def rename(path1, path2):
    retval = hw3lib.hw3_rename(path1, path2)
    if verbose:
        print('rename(%s,%s) = %d' % (path1, path2, retval))
    return retval

def chmod(path, mode):
    retval = hw3lib.hw3_chmod(path, c_int(mode))
    if verbose:
        print('chmod(%s) = %d' % (path, retval))
    return retval

def utime(path, actime, modtime):
    retval = hw3lib.hw3_utime(path, c_int(actime), c_int(modtime))
    if verbose:
        print('utime(%s,%d,%d) = %d' % (path, actime, modtime, retval))
    return retval

def read(path, len, offset):
    buf = (c_char * len)()
    val = hw3lib.hw3_read(xbytes(path), buf, c_int(len), c_int(offset), byref(null_fi))
    if verbose:
        print('read(%s,%d,%d) = %d' % (path, len, offset, val))
    if val < 0:
        return val,''
    return val, buf[0:val]

def write(path, data, offset):
    nbytes = len(data)
    val = hw3lib.hw3_write(path, xbytes(data), c_int(nbytes),
                               c_int(offset), byref(null_fi))
    if verbose:
        print('write(%s,%d,%d) = %d' % (path, nbytes, offset, val))
    return val

def statfs():
    st = statvfs()
    retval = hw3lib.hw3_statfs('/', byref(st))
    if verbose:
        print('statfs() = %d (%s)' % (retval, str(st)))
    return retval,st

# Constants

S_IFMT  = 0o0170000  # bit mask for the file type bit field
S_IFREG = 0o0100000  # regular file
S_IFDIR = 0o0040000  # directory

EPERM = 1            # Error codes
ENOENT = 2           # ...
EIO = 5
ENOMEM = 12
ENOTDIR = 20
EISDIR = 21
EINVAL = 22
ENOSPC = 28
EOPNOTSUPP = 95
EEXIST = 17
ENOTEMPTY = 39

errors = { EPERM : 'EPERM', ENOENT : 'ENOENT', EIO : 'EIO',
               ENOMEM : 'ENOMEM', ENOTDIR : 'ENOTDIR',
               EISDIR : 'EISDIR', EINVAL : 'EINVAL',
               ENOSPC : 'ENOSPC', EOPNOTSUPP : 'EOPNOTSUPP',
               EEXIST : 'EEXIST', ENOTEMPTY : 'ENOTEMPTY'}

def strerr(err):
    if err < 0:
        err = -err
    else:
        return "OK"
    if err in errors:
        return errors[err]
    return 'UNKNOWN (%d)' % err
