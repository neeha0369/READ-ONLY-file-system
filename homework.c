/*
 * file:        homework.c
 * description: skeleton file for CS 5600 system
 *
 * CS 5600, Computer Systems, Northeastern CCIS
 * Peter Desnoyers, November 2019
 */

#define FUSE_USE_VERSION 27
#define _FILE_OFFSET_BITS 64

#include <stdlib.h>
#include <stddef.h>
#include <unistd.h>
#include <fuse.h>
#include <fcntl.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>

#include "fs5600.h"

/* disk access. All access is in terms of 4KB blocks; read and
 * write functions return 0 (success) or -EIO.
 */
extern int block_read(void *buf, int lba, int nblks);
extern int block_write(void *buf, int lba, int nblks);

int bit_test(unsigned char *map, int i) {
    return map[i/8] & (1 << (i%8));
}

struct fs_super *super_block;
unsigned char *bitmap;
struct fs_inode *root_inode;
struct fs_dirent *root_dir;

/* init - this is called once by the FUSE framework at startup. Ignore
 * the 'conn' argument.
 * recommended actions:
 *   - read superblock
 *   - allocate memory, read bitmaps and inodes
 */
void* fs_init(struct fuse_conn_info *conn)
{
    // get super block
    super_block = (struct fs_super *)calloc(1, FS_BLOCK_SIZE);
    block_read((void *)super_block, 0, 1);

    // get bitmap
    // If you allocate a character array of 4096 bytes and read block 1 into it, 
    // you can pass it to the bit_test function.
    bitmap = (unsigned char *)calloc(1, FS_BLOCK_SIZE);
    block_read((void *)bitmap, 1, 1);

    // get root dir
    root_inode = (struct fs_inode *)calloc(1, FS_BLOCK_SIZE);
    block_read((void *)root_inode, 2, 1);

    root_dir = (struct fs_dirent *)calloc(1, FS_BLOCK_SIZE);
    root_dir->valid = 1;
    strcpy(root_dir->name, "/");
    root_dir->inode = 2;

    return NULL;
}

/* Note on path translation errors:
 * In addition to the method-specific errors listed below, almost
 * every method can return one of the following errors if it fails to
 * locate a file or directory corresponding to a specified path.
 *
 * ENOENT - a component of the path doesn't exist.
 * ENOTDIR - an intermediate component of the path (e.g. 'b' in
 *           /a/b/c) is not a directory
 */

/* note on splitting the 'path' variable:
 * the value passed in by the FUSE framework is declared as 'const',
 * which means you can't modify it. The standard mechanisms for
 * splitting strings in C (strtok, strsep) modify the string in place,
 * so you have to copy the string and then free the copy when you're
 * done. One way of doing this:
 *
 *    char *_path = strdup(path);
 *    int inum = translate(_path);
 *    free(_path);
 */

// REF: https://piazza.com/class/k0e22qng8934of?cid=246
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

char **getArgvArr() {
    char **argv = (char **) calloc(MAX_PATH_LEN, sizeof(char *));
    for (int i = 0; i < MAX_PATH_LEN; i++) {
        argv[i] = calloc(MAX_NAME_LEN, sizeof(char *));
    }

    return argv;
}

struct fs_dirent* translatePath(const char *path) {
    char *c_path = strdup(path);
    char **argv = getArgvArr();
    int length = parse(c_path, argv);

    struct fs_inode* parent_inode;
    struct fs_dirent* parent_entry = root_dir;

    for (int i = 0; i < length; i++) {
        int not_found_flag = 1;
        parent_inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int has_read = block_read((void*) parent_inode, parent_entry->inode, 1);

        if (has_read != 0 || (S_ISREG(parent_inode->mode) && i < length - 1))
            return NULL;

        for (int j = 0; j < (FS_BLOCK_SIZE/4 - 5); j++) {
            struct fs_dirent* dir_entry = (struct fs_dirent*) calloc(1, FS_BLOCK_SIZE);
            int is_read = block_read((void*) dir_entry, parent_inode->ptrs[j], 1);

            if (is_read != 0)
                return NULL;

            for (int k = 0; k < MAX_DIR_ENTRIES; k++) {
                 if (dir_entry[k].valid == 1 && strcmp(dir_entry[k].name, argv[i]) == 0) {
                    // directory is valid
                    parent_entry = &dir_entry[k];
                    not_found_flag = 0;
                    break;
                }
            }

            if (not_found_flag == 0)
                break;
        }

        if (not_found_flag == 1)
            return NULL;
    }

    return parent_entry;
}

struct fs_dirent* translatePathBlock(const char *path) {
    char *c_path = strdup(path);
    char **argv = getArgvArr();
    int length = parse(c_path, argv);

    struct fs_inode* parent_inode;
    struct fs_dirent* parent_entry = root_dir;
    struct fs_dirent* block;

    for (int i = 0; i < length; i++) {
        int not_found_flag = 1;
        parent_inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int has_read = block_read((void*) parent_inode, parent_entry->inode, 1);

        if (has_read != 0 || (S_ISREG(parent_inode->mode) && i < length - 1))
            return NULL;

        for (int j = 0; j < (FS_BLOCK_SIZE/4 - 5); j++) {
            struct fs_dirent* dir_entry = (struct fs_dirent*) calloc(1, FS_BLOCK_SIZE);
            int is_read = block_read((void*) dir_entry, parent_inode->ptrs[j], 1);

            if (is_read != 0)
                return NULL;

            for (int k = 0; k < MAX_DIR_ENTRIES; k++) {
                 if (dir_entry[k].valid == 1 && strcmp(dir_entry[k].name, argv[i]) == 0) {
                    // directory is valid
                    parent_entry = &dir_entry[k];
                    block = dir_entry;
                    not_found_flag = 0;
                    break;
                }
            }

            if (not_found_flag == 0)
                break;
        }

        if (not_found_flag == 1)
            return NULL;
    }

    return block;
}

uint32_t translatePathParentNo(const char *path) {
    char *c_path = strdup(path);
    char **argv = getArgvArr();
    int length = parse(c_path, argv);
    uint32_t parent_block_no = 0; 

    struct fs_inode* parent_inode;
    struct fs_dirent* parent_entry = root_dir;

    for (int i = 0; i < length; i++) {
        int not_found_flag = 1;
        parent_inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int has_read = block_read((void*) parent_inode, parent_entry->inode, 1);

        if (has_read != 0 || (S_ISREG(parent_inode->mode) && i < length - 1))
            return 0;

        for (int j = 0; j < (FS_BLOCK_SIZE/4 - 5); j++) {
            struct fs_dirent* dir_entry = (struct fs_dirent*) calloc(1, FS_BLOCK_SIZE);
            int is_read = block_read((void*) dir_entry, parent_inode->ptrs[j], 1);

            if (is_read != 0)
                return 0;

            for (int k = 0; k < MAX_DIR_ENTRIES; k++) {
                 if (dir_entry[k].valid == 1 && strcmp(dir_entry[k].name, argv[i]) == 0) {
                    // directory is valid
                    parent_entry = &dir_entry[k];
                    parent_block_no = parent_inode->ptrs[j];
                    not_found_flag = 0;
                    break;
                }
            }

            if (not_found_flag == 0)
                break;
        }

        if (not_found_flag == 1)
            return 0;
    }

    return parent_block_no;
}

void assignAttributes(struct fs_inode* inode, struct stat* sb) {
    // REF: https://linux.die.net/man/2/lstat
    sb->st_dev = 0;
    sb->st_ino = 0;
    sb->st_mode = inode->mode;
    sb->st_nlink = 1;
    sb->st_uid = inode->uid;
    sb->st_gid = inode->gid;
    sb->st_rdev = 0;
    sb->st_size = inode->size;
    sb->st_blksize = inode->size;
    sb->st_blocks = inode->size/FS_BLOCK_SIZE;
    sb->st_atime = inode->mtime;
    sb->st_mtime = inode->mtime;
    sb->st_ctime = inode->mtime;
}


/* getattr - get file or directory attributes. For a description of
 *  the fields in 'struct stat', see 'man lstat'.
 *
 * Note - for several fields in 'struct stat' there is no corresponding
 *  information in our file system:
 *    st_nlink - always set it to 1
 *    st_atime, st_ctime - set to same value as st_mtime
 *
 * errors - path translation, ENOENT
 */
int fs_getattr(const char *path, struct stat *sb) {
    struct fs_dirent* dir = translatePath(path);

    if (dir == NULL)
        return -ENOENT;
    else {
        struct fs_inode* inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int is_read = block_read((void*)inode, dir->inode, 1);

        if (is_read != 0)
            return ENOENT;

        assignAttributes(inode, sb);
        return 0;
    }
}

/* readdir - get directory contents.
 *
 * call the 'filler' function once for each valid entry in the 
 * directory, as follows:
 *     filler(buf, <name>, <statbuf>, 0)
 * where <statbuf> is a pointer to struct stat, just like in getattr.
 *
 * Errors - path resolution, ENOTDIR, ENOENT
 */
int fs_readdir(const char *path, void *ptr, fuse_fill_dir_t filler,
		       off_t offset, struct fuse_file_info *fi)
{
    struct fs_dirent* dir = translatePath(path);
    if (dir == NULL)
        return -ENOENT;
    else {
        struct fs_inode* dir_inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int has_read = block_read((void *)dir_inode, dir->inode, 1);
        
        if (S_ISREG(dir_inode->mode))
            return -ENOTDIR;

        if (has_read != 0)
            return -ENOENT;
        
        // call the 'filler' function once for each valid entry in the directory
        for (int j = 0; j < (FS_BLOCK_SIZE/4 - 5); j++) {
            struct fs_dirent* dir_entry = (struct fs_dirent*) calloc(1, FS_BLOCK_SIZE);
            int is_read = block_read((void*) dir_entry, dir_inode->ptrs[j], 1);

            if (is_read != 0)
                return -ENOENT;

            for (int k = 0; k < MAX_DIR_ENTRIES; k++) {
                if (dir_entry[k].valid == 1) {
                    struct stat *sb = (struct stat*) calloc(1, sizeof(struct stat *));
                    filler(ptr, dir_entry[k].name, sb, 0);
                }   
            }
        }

        return 0;
    }
}


/* rename - rename a file or directory
 * Errors - path resolution, ENOENT, EINVAL, EEXIST
 *
 * ENOENT - source does not exist
 * EEXIST - destination already exists
 * EINVAL - source and destination are not in the same directory
 *
 * Note that this is a simplified version of the UNIX rename
 * functionality - see 'man 2 rename' for full semantics. In
 * particular, the full version can move across directories, replace a
 * destination file, and replace an empty directory with a full one.
 */
int fs_rename(const char *src_path, const char *dst_path) {
    struct fs_dirent* src_dir = translatePath(src_path);
    struct fs_dirent* dst_dir = translatePath(dst_path);

    if (src_dir == NULL)
        return -ENOENT;
    else if (dst_dir != NULL)
        return -EEXIST;
    else {
        char *c_src_path = strdup(src_path);
        char *c_dst_path = strdup(dst_path);
        char **src_argv = getArgvArr();
        char **dst_argv = getArgvArr();
        int src_path_len = parse(c_src_path, src_argv);
        int dst_path_len = parse(c_dst_path, dst_argv);

        if (src_path_len != dst_path_len)
            return -EINVAL;
        else {
            // check path till parent directory
            for (int i = 0; i < src_path_len-1; i++) {
                if (c_src_path[i] != c_dst_path[i])
                    return -EINVAL;
            }

            uint32_t parent_block_no = translatePathParentNo(src_path);
            struct fs_dirent* block = translatePathBlock(src_path);
            int file_loc = 0;

            for (int i = 0; i < MAX_DIR_ENTRIES; i++) {
                if (block[i].valid == 1 && strcmp(block[i].name, src_argv[src_path_len - 1]) == 0) {
                    file_loc = i;
                    break;
                } 
            } 

            if (parent_block_no == 0)
                return -ENOENT;

            // source and destination in same directory
            strcpy(block[file_loc].name, dst_argv[dst_path_len - 1]);
            block_write((void*)block, parent_block_no, 1);
            return 0;
        }
    }
}

/* chmod - change file permissions
 * utime - change access and modification times
 *         (for definition of 'struct utimebuf', see 'man utime')
 *
 * Errors - path resolution, ENOENT.
 */
int fs_chmod(const char *path, mode_t mode) {
    struct fs_dirent* dir = translatePath(path);
    if (dir == NULL)
        return -ENOENT;
    else {
        struct fs_inode* inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int is_read = block_read((void*) inode, dir->inode, 1);

        if (is_read != 0)
            return -ENOENT;

        inode->mode = mode;
        // REF: https://stackoverflow.com/a/11765384
        inode->mtime = (unsigned) time(NULL);
        block_write((void*)inode, dir->inode, 1);
        return 0;
    }
}


/* read - read data from an open file.
 * should return exactly the number of bytes requested, except:
 *   - if offset >= file len, return 0
 *   - if offset+len > file len, return bytes from offset to EOF
 *   - on error, return <0
 * Errors - path resolution, ENOENT, EISDIR
 */
int fs_read(const char *path, char *buf, size_t len, off_t offset,
	    struct fuse_file_info *fi) {
    struct fs_dirent* file = translatePath(path);
    uint32_t bytes_read = 0;

    if (file == NULL)
        return -ENOENT;
    else {
        struct fs_inode* file_inode = (struct fs_inode*) calloc(1, FS_BLOCK_SIZE);
        int has_read = block_read((void *)file_inode, file->inode, 1);
        int32_t total_size = file_inode->size;

        if (offset + len > total_size)
            len = total_size - offset;

        // REF: https://piazza.com/class/k0e22qng8934of?cid=268
        // REF: https://linux.die.net/man/2/lstat
        if (S_ISDIR(file_inode->mode))
            return -EISDIR;

        if (has_read != 0)
            return -ENOENT;

        if (offset >= file_inode->size)
            return 0;
        else {
            for (int i = 0; i < (FS_BLOCK_SIZE/4 - 5); i++) {
                // offset 4096 is in 2nd block
                if (offset/FS_BLOCK_SIZE > 0) {
                    offset -= FS_BLOCK_SIZE;
                    total_size -= FS_BLOCK_SIZE;
                }   
                else {
                    char* data_block = (char*) calloc(1, FS_BLOCK_SIZE);
                    int is_read = block_read((void *)data_block, file_inode->ptrs[i], 1);

                    if (is_read != 0)
                        continue;    

                    if (offset + len < FS_BLOCK_SIZE) {
                        memcpy(buf, data_block + offset, len);
                        bytes_read += len;
                        len = 0;
                        break;   
                    }
                    else {
                        memcpy(buf, data_block + offset, FS_BLOCK_SIZE - offset);
                        buf += (FS_BLOCK_SIZE - offset);
                        len -= (FS_BLOCK_SIZE - offset);
                        total_size -= (FS_BLOCK_SIZE - offset);
                        bytes_read += (FS_BLOCK_SIZE - offset);
                        offset = 0;
                    }
                }
                
            }
        }
    }
    
    if (len <= 0)
        return bytes_read;
    else
        return -ENOENT;
}

uint32_t getFreeBlocksCount() {
    uint32_t total = 0;
    for (uint32_t i = 2; i < super_block->disk_size; i++) {
        if (bit_test(bitmap, i) == 0)
            total++;
    }

    return total;
}


/* statfs - get file system statistics
 * see 'man 2 statfs' for description of 'struct statvfs'.
 * Errors - none. Needs to work.
 */
int fs_statfs(const char *path, struct statvfs *st) {
    /* needs to return the following fields (set others to zero):
     *   f_bsize = BLOCK_SIZE
     *   f_blocks = total image - (superblock + block map)
     *   f_bfree = f_blocks - blocks used
     *   f_bavail = f_bfree
     *   f_namelen = <whatever your max namelength is>
     *
     * it's OK to calculate this dynamically on the rare occasions
     * when this function is called.
     */
    // REF: http://man7.org/linux/man-pages/man2/statfs.2.html
    uint32_t free_blocks_count = getFreeBlocksCount();
    st->f_bsize = FS_BLOCK_SIZE;
    st->f_blocks = super_block->disk_size - 2;
    st->f_bfree = free_blocks_count;
    st->f_bavail = free_blocks_count;
    st->f_namemax = MAX_NAME_LEN;
    st->f_files = 0;
    st->f_ffree = 0;
    st->f_fsid = 0;
    st->f_frsize = 0;
    st->f_flag = 0;
    
    return 0;
}

/* operations vector. Please don't rename it, or else you'll break things
 */
struct fuse_operations fs_ops = {
    .init = fs_init,
    .getattr = fs_getattr,
    .readdir = fs_readdir,
    .rename = fs_rename,
    .chmod = fs_chmod,
    .read = fs_read,
    .statfs = fs_statfs,
};

