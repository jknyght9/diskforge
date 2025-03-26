# MBR/GPT Example Disk Image Creator

This project creates a 512 MB disk image for both MBR and GPT partitioning schemes. It also creates four partitions and formats them with the following configuration:

| Filesystem  | Size  |
| ----------- | ----- |
| FAT32       | +200M |
| NTFS        | +200M |
| Ext3        | +200M |
| exFAT       | +200M |
| Unallocated | ~     |

The purpose of this project is to familiarize students with MBR and GPT partitioning scheme.

## Usage

Use the docker file to build out the image files.

```sh
# Build the container
docker build -t disk-image-example

# Build the image files
docker run --rm --privileged -v $(pwd)/output:/output -v $(pwd)/files:/files disk-image-example
```

## Analyzing Images

> Install **sleuthkit** and run the following commands.

View the partition tables.

```sh
# Partition tables for MBR and GPT
usename@hostname:/$ mmls output/mbr_disk.img

DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000002047   0000002048   Unallocated
002:  000:000   0000002048   0000206847   0000204800   Win95 FAT32 (0x0c)
003:  000:001   0000206848   0000411647   0000204800   NTFS / exFAT (0x07)
004:  000:002   0000411648   0000616447   0000204800   Linux (0x83)
005:  000:003   0000616448   0000821247   0000204800   NTFS / exFAT (0x07)
006:  -------   0000821248   0001048575   0000227328   Unallocated


username@hostname:/$ mmls output/gpt_disk.img

GUID Partition Table (EFI)
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Safety Table
001:  -------   0000000000   0000002047   0000002048   Unallocated
002:  Meta      0000000001   0000000001   0000000001   GPT Header
003:  Meta      0000000002   0000000033   0000000032   Partition Table
004:  000       0000002048   0000206847   0000204800   primary
005:  001       0000206848   0000411647   0000204800   primary
006:  002       0000411648   0000616447   0000204800   primary
007:  003       0000616448   0000821247   0000204800   primary
008:  -------   0000821248   0001048575   0000227328   Unallocated

```

View the first partition in both MBR and GPT images.

```sh
# FAT32 partition for MBR and GPT

username@hostname:/$ fsstat -o 2048 output/mbr_disk.img

FILE SYSTEM INFORMATION
--------------------------------------------
File System Type: FAT32

OEM Name: mkfs.fat
Volume ID: 0x97f55ca5
Volume Label (Boot Sector): MBR_FAT32
Volume Label (Root Directory): MBR_FAT32
File System Type Label: FAT32
Next Free Sector (FS Info): 3184
Free Sector Count (FS Info): 201615

Sectors before file system: 0

File System Layout (in sectors)
Total Range: 0 - 204799
* Reserved: 0 - 31
** Boot Sector: 0
** FS Info Sector: 1
** Backup Boot Sector: 6
* FAT 0: 32 - 1607
* FAT 1: 1608 - 3183
* Data Area: 3184 - 204799
** Cluster Area: 3184 - 204799
*** Root Directory: 3184 - 3184

METADATA INFORMATION
--------------------------------------------
Range: 2 - 3225862
Root Directory: 2

CONTENT INFORMATION
--------------------------------------------
Sector Size: 512
Cluster Size: 512
Total Cluster Range: 2 - 201617

FAT CONTENTS (in sectors)
--------------------------------------------
3184-3184 (1) -> EOF

username@hostname:/$ fsstat -o 2048 output/gpt_disk.img

FILE SYSTEM INFORMATION
--------------------------------------------
File System Type: FAT32

OEM Name: mkfs.fat
Volume ID: 0x97fb0c26
Volume Label (Boot Sector): GPT_FAT32
Volume Label (Root Directory): GPT_FAT32
File System Type Label: FAT32
Next Free Sector (FS Info): 3184
Free Sector Count (FS Info): 201615

Sectors before file system: 0

File System Layout (in sectors)
Total Range: 0 - 204799
* Reserved: 0 - 31
** Boot Sector: 0
** FS Info Sector: 1
** Backup Boot Sector: 6
* FAT 0: 32 - 1607
* FAT 1: 1608 - 3183
* Data Area: 3184 - 204799
** Cluster Area: 3184 - 204799
*** Root Directory: 3184 - 3184

METADATA INFORMATION
--------------------------------------------
Range: 2 - 3225862
Root Directory: 2

CONTENT INFORMATION
--------------------------------------------
Sector Size: 512
Cluster Size: 512
Total Cluster Range: 2 - 201617

FAT CONTENTS (in sectors)
--------------------------------------------
3184-3184 (1) -> EOF
```

Use a hexeditor to view the first 512 bytes of the MBR partition.

```sh
username@hostname:/$ xxd -l 512 -g 1 output/mbr_disk.img

00000000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000020: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000030: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000040: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000050: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000060: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000070: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000080: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000090: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000000a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000000b0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000000c0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000000d0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000000e0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000000f0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000100: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000110: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000120: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000130: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000140: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000150: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000160: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000170: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000190: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000001a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
000001b0: 00 00 00 00 00 00 00 00 64 f4 ee 2d 00 00 00 20  ........d..-...
000001c0: 21 00 0c df 13 0c 00 08 00 00 00 20 03 00 00 df  !.......... ....
000001d0: 14 0c 07 9f 06 19 00 28 03 00 00 20 03 00 00 9f  .......(... ....
000001e0: 07 19 83 5e 38 26 00 48 06 00 00 20 03 00 00 5e  ...^8&.H... ...^
000001f0: 39 26 07 1e 2b 33 00 68 09 00 00 20 03 00 55 aa  9&..+3.h... ..U.
```

Use a hexeditor to read the GPT header in sector 1.

```sh
username@hostname:/$ xxd -l 92 -g 1 -s 512 output/gpt_disk.img

00000200: 45 46 49 20 50 41 52 54 00 00 01 00 5c 00 00 00  EFI PART....\...
00000210: e1 6f c0 b0 00 00 00 00 01 00 00 00 00 00 00 00  .o..............
00000220: ff ff 0f 00 00 00 00 00 22 00 00 00 00 00 00 00  ........".......
00000230: de ff 0f 00 00 00 00 00 23 b0 30 15 13 9f 52 4b  ........#.0...RK
00000240: a1 e5 57 ba f4 62 d0 1e 02 00 00 00 00 00 00 00  ..W..b..........
00000250: 80 00 00 00 80 00 00 00 75 e9 42 82              ........u.B.
```
