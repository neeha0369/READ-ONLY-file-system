#!/usr/bin/python
import unittest
import hw3test as hw3
import zlib

def cksum(str):
    return zlib.crc32(str) & 0xffffffff

class tests(unittest.TestCase):
    ##### fs_statfs #####
    def test_1_statfs(self):
        v,sfs = hw3.statfs()
        self.assertTrue(v == 0)
        self.assertTrue(sfs.f_bsize == 4096)    # defined in fs5600.h
        self.assertTrue(sfs.f_blocks == 398)    # test.img - 400 blocks - super - bitmap
        self.assertTrue(sfs.f_bfree == 355)     # test.img
        self.assertTrue(sfs.f_namemax == 27)    # again from FS definition


    ##### fs_getattr #####
    # root
    def test_2_getattr(self):
        retval, sb = hw3.getattr("/")
        self.assertTrue(retval == 0)
        self.assertTrue(sb.st_uid == 0)
        self.assertTrue(sb.st_gid == 0)
        self.assertTrue(sb.st_mode == int("40777", 8)) 

    # /file.1k
    def test_3_getattr(self):
        retval, sb = hw3.getattr("/file.1k")
        self.assertTrue(retval == 0)
        self.assertTrue(sb.st_uid == 500)
        self.assertTrue(sb.st_gid == 500)
        self.assertTrue(sb.st_size == 1000)
        self.assertTrue(sb.st_mode == int("100666", 8))

    # /dir2/file.4k+
    def test_4_getattr(self):
        retval, sb = hw3.getattr("/dir2/file.4k+")
        self.assertTrue(retval == 0)
        self.assertTrue(sb.st_uid == 500)
        self.assertTrue(sb.st_gid == 500)
        self.assertTrue(sb.st_size == 4098)
        self.assertTrue(sb.st_mode == int("100777", 8))

    # /dir1/file.2k
    # dir1 doesn't exist
    def test_5_getattr(self):
        retval, sb = hw3.getattr("/dir1/file.2k")
        self.assertTrue(retval == -hw3.ENOENT)

    # /dir2/file.2k
    # file.2k doesn't exist
    def test_6_getattr(self):
        retval, sb = hw3.getattr("/dir2/file.2k")
        self.assertTrue(retval == -hw3.ENOENT)

    # /dir-with-long-name/file.12k+
    def test_7_getattr(self):
        retval, sb = hw3.getattr("/dir-with-long-name/file.12k+")
        self.assertTrue(retval == 0)
        self.assertTrue(sb.st_uid == 0)
        self.assertTrue(sb.st_gid == 500)
        self.assertTrue(sb.st_size == 12289)
        self.assertTrue(sb.st_mode == int("100666", 8))

    # /dir3/subdir/file.4k-
    def test_8_getattr(self):
        retval, sb = hw3.getattr("/dir3/subdir/file.4k-")
        self.assertTrue(retval == 0)
        self.assertTrue(sb.st_uid == 500)
        self.assertTrue(sb.st_gid == 500)
        self.assertTrue(sb.st_size == 4095)
        self.assertTrue(sb.st_mode == int("100666", 8))


    ##### fs_readdir #####
    # root
    def test_9_readdir(self):
        val, dirs = hw3.readdir("/")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[0].name == "file.1k")
        self.assertTrue(dirs[1].name == "file.10")
        self.assertTrue(dirs[2].name == "dir-with-long-name")
        self.assertTrue(dirs[3].name == "dir2")
        self.assertTrue(dirs[4].name == "dir3")
        self.assertTrue(dirs[5].name == "file.12k+")
        self.assertTrue(dirs[6].name == "file.8k+")

    # /dir2
    def test_10_readdir(self):
        val, dirs = hw3.readdir("/dir2")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[0].name == "twenty-seven-byte-file-name")
        self.assertTrue(dirs[1].name == "file.4k+")

    # not a directory
    def test_11_readdir(self):
        val, dirs = hw3.readdir("/file.1k")
        self.assertTrue(val == -hw3.ENOTDIR)

    # incorrect path
    def test_12_readdir(self):
        val, dirs = hw3.readdir("/file.2k")
        self.assertTrue(val == -hw3.ENOENT)


    ##### fs_rename #####
        
    # /file.1k to /file.10 - destination already exists
    def test_13_rename(self):
        val = hw3.rename("/file.1k", "/file.10")
        self.assertTrue(val == -hw3.EEXIST)

    # /file.122k - source does not exist
    def test_14_rename(self):
        val = hw3.rename("/file.122k", "/file.11")
        self.assertTrue(val == -hw3.ENOENT)
        
    # /file.1k to /dir2/file.4k+ - src and dest not in same directory
    def test_15_rename(self):
        val = hw3.rename("/file.1k", "/dir2/file.5k+")
        self.assertTrue(val == -hw3.EINVAL)
        
    # /file.1k to /file.11k+ - no error thrown for correct name change
    def test_16_rename(self):
        val = hw3.rename("/file.1k", "/file.11k+")
        self.assertTrue(val == 0)

    # root - check if renamed
    def test_17_readdir(self):
        val, dirs = hw3.readdir("/")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[0].name == "file.11k+")

    # rename back
    def test_18_rename(self):
        val = hw3.rename("/file.11k+", "/file.1k")
        self.assertTrue(val == 0)

    # no error thrown for correct name change
    def test_19_rename(self):
        val = hw3.rename("/dir2/file.4k+", "/dir2/file.3k+")
        self.assertTrue(val == 0)
    
    # root - check if renamed
    def test_20_readdir(self):
        val, dirs = hw3.readdir("/dir2")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[1].name == "file.3k+")

    # rename back
    def test_21_rename(self):
        val = hw3.rename("/dir2/file.3k+", "/dir2/file.4k+")
        self.assertTrue(val == 0)

    # sub-directory name change
    def test_22_rename(self):
        val = hw3.rename("/dir3/subdir", "/dir3/subdir2")
        self.assertTrue(val == 0)
    
    # root - check if renamed
    def test_23_readdir(self):
        val, dirs = hw3.readdir("/dir3")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[0].name == "subdir2")

    # rename back
    def test_24_rename(self):
        val = hw3.rename("/dir3/subdir2", "/dir3/subdir")
        self.assertTrue(val == 0)

    # no error thrown for correct directory name change
    def test_25_rename(self):
        val = hw3.rename("/dir2", "/dir22")
        self.assertTrue(val == 0)
        
    # root - check if directory is renamed
    def test_26_readdir(self):
        val, dirs = hw3.readdir("/")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[3].name == "dir22")

    # rename directory back
    def test_27_rename(self):
        val = hw3.rename("/dir22", "/dir2")
        self.assertTrue(val == 0)

    # check if directory is renamed back
    def test_28_readdir(self):
        val, dirs = hw3.readdir("/")
        self.assertTrue(val == 0)
        self.assertTrue(dirs[3].name == "dir2")

    ##### fs_chmod #####

    # /file.10
    def test_29_chmod(self):
        val = hw3.chmod("/file.10", 0o100777)   
        self.assertEqual(val, 0)     
        
    # check if permisions changed
    def test_30_getattr(self):
        retval, sb = hw3.getattr("/file.10")
        self.assertTrue(sb.st_mode == int("100777", 8))

    # revert back permissions
    def test_31_chmod(self):
        val = hw3.chmod("/file.10", 0o100666)   
        self.assertEqual(val, 0)
     
    # change permission for dir
    def test_32_chmod(self):
        val = hw3.chmod("/dir2", 0o40666)
        self.assertEqual(val, 0)

    # check the changed permisions for dir and check
    def test_33_getattr(self):
        retval, sb = hw3.getattr("/dir2")
        self.assertTrue(sb.st_mode == int("40666", 8))

    # revert back permissions
    def test_34_chmod(self):
        val = hw3.chmod("/dir2", 0o40777)
        self.assertEqual(val, 0)
        
    # no dir exist to change the permissions
    def test_35_chmod(self):
        # /dir22 does not exist
        val = hw3.chmod("/dir22", 0o40777)
        self.assertEqual(val, -hw3.ENOENT)

    # no file exist to change the permissions
    def test_36_chmod(self):
        # /dir22/file.10 does not exist
        val = hw3.chmod("/dir2/file.10", 0o100777)
        self.assertEqual(val, -hw3.ENOENT)

    ##### fs_read #####

    # read file /file.1k, len = 1100, offset = 0
    def test_37_read(self):
        data = 'K' * 276177 # see description above
        v,data = hw3.read("/file.1k", 1100, 0) # offset = 0
        self.assertEqual(v, 1000) 
        self.assertEqual(len(data), 1000) 
        self.assertEqual(cksum(data), 1786485602)

    def test_38_read(self):
        data = 'K' * 276177 # see description above
        v,data = hw3.read("/file.1k", 10000, 0) # offset = 0
        self.assertEqual(v, 1000) 
        self.assertEqual(len(data), 1000) 
        self.assertEqual(cksum(data), 1786485602)
    
    #  offset+len > file len
    def test_39_read(self):
        data = 'K' * 276177 # see description above
        v,data = hw3.read("/dir3/file.12k-", 15000, 0) # offset = 0
        self.assertEqual(v, 12287) 
        self.assertEqual(len(data), 12287) 
        self.assertEqual(cksum(data), 2954788945)

    # reading dir - EISDIR
    def test_40_read(self):
        data = 'K' * 276177 # see description above
        v,data = hw3.read("/dir3", 15000, 0) # offset = 0
        self.assertEqual(v, -hw3.EISDIR) 

    # reading dir - ENOENT
    def test_41_read(self):
        data = 'K' * 276177 # see description above
        v,data = hw3.read("/dir3/file.10", 15000, 0) # offset = 0
        self.assertEqual(v, -hw3.ENOENT)

    # offset greater than file len
    def test_42_read(self):
        data = 'K' * 276177 # see description above
        v,data = hw3.read("/file.1k", 1000, 1000) # offset = 0
        self.assertEqual(v, 0)

    # multiple small reads
    def test_43_read(self):
        data = 'K' * 276177 # see description above
        v1,data1 = hw3.read("/dir2/file.4k+", 1000, 0) # offset = 0
        self.assertEqual(v1, 1000) 
        self.assertEqual(len(data1), 1000) 
        v2,data2 = hw3.read("/dir2/file.4k+", 17, 1000) # offset = 0
        self.assertEqual(v2, 17) 
        self.assertEqual(len(data2), 17) 
        v3,data3 = hw3.read("/dir2/file.4k+", 100, 1017) # offset = 0
        self.assertEqual(v3, 100) 
        self.assertEqual(len(data3), 100) 
        v4,data4 = hw3.read("/dir2/file.4k+", 1000, 1117) # offset = 0
        self.assertEqual(v4, 1000) 
        self.assertEqual(len(data4), 1000)
        v5,data5 = hw3.read("/dir2/file.4k+", 1024, 2117) # offset = 0
        self.assertEqual(v5, 1024) 
        self.assertEqual(len(data5), 1024)  
        v6,data6 = hw3.read("/dir2/file.4k+", 1970, 3141) # offset = 0
        self.assertEqual(v6, 957) 
        self.assertEqual(len(data6), 957)  
        v7,data7 = hw3.read("/dir2/file.4k+", 3000, 5111) # offset = 0
        self.assertEqual(v7, 0) 
        self.assertEqual(len(data7), 0) 
        total_data = data1 + data2 + data3 + data4 + data5 + data6 + data7
        v_total = v1 + v2 + v3 + v4 + v5 + v6 + v7
        self.assertEqual(v_total, 4098) 
        self.assertEqual(len(total_data), 4098) 
        self.assertEqual(cksum(total_data), 799580753)

if __name__ == '__main__':
    hw3.init('test.img')
    unittest.main()
