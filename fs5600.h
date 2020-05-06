/*
 * file:        fsx600.h
 * description: Data structures for CS 5600/7600 file system.
 *
 * CS 5600, Computer Systems, Northeastern CCIS
 * Peter Desnoyers,  November 2016
 */
#ifndef __CSX600_H__
#define __CSX600_H__

#define FS_BLOCK_SIZE 4096
#define FS_MAGIC 0x37363030
#define MAX_PATH_LEN 10
#define MAX_NAME_LEN 27
#define MAX_DIR_ENTRIES 128

/* how many buckets of size M do you need to hold N items? 
 */
#define DIV_ROUND_UP(N, M) ((N) + (M) - 1) / (M)

/* Entry in a directory
 */
struct fs_dirent {
    uint32_t valid : 1;
    uint32_t inode : 31;
    char name[28];              /* with trailing NUL */
};

/* Superblock - holds file system parameters. 
 */
struct fs_super {
    uint32_t magic;
    uint32_t disk_size;         /* in blocks */
    
    /* pad out to an entire block */
    char pad[FS_BLOCK_SIZE - 2 * sizeof(uint32_t)]; 
};

struct fs_inode {
    uint16_t uid;
    uint16_t gid;
    uint32_t mode;
    uint32_t ctime;
    uint32_t mtime;
    int32_t  size;
    uint32_t ptrs[FS_BLOCK_SIZE/4 - 5]; /* inode = 4096 bytes */
};

#endif


