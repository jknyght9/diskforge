# DiskForge

**DiskForge** is a Python-based tool for generating partitioned and encrypted disk images for digital forensics training, incident response simulations, CTF challenges, and lab environments.

Define disk layouts, filesystems, encryption, and file population rules in a JSON manifest — then build reproducible disk images with a single Docker command.

**[Full Documentation](https://jknyght9.github.io/diskforge)**

---

## Features

- MBR and GPT partition table support
- Primary, extended, and logical partitions
- Multiple filesystems: FAT32, NTFS, EXT2/3/4, XFS, exFAT
- LUKS encryption (v1/v2) at the partition level
- VeraCrypt full-disk encryption
- File population with add, copy, move, and delete operations
- Wildcard and glob pattern support for file operations
- Multi-disk builds from a single manifest
- Automated test and verification suite
- Dockerized and reproducible

---

## Quick Start

### 1. Clone and build

```bash
git clone https://github.com/jknyght9/diskforge.git
cd diskforge
docker build -t diskforge .
```

### 2. Define a manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training-usb",
      "type": "GPT",
      "size": "512M",
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "fat32",
          "label": "EVIDENCE",
          "size": "500M",
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/secret_notes.txt"]
          }
        }
      ]
    }
  ]
}
```

### 3. Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/output:/output" \
  diskforge /manifests/manifest.json
```

Output `.img` files are placed in the `output/` directory.

---

## Encryption

### LUKS (partition-level)

Add an `encrypt` block to any partition. Supported on ext2/3/4 and xfs.

```json
{
  "number": 1,
  "type": "primary",
  "filesystem": "ext4",
  "size": "500M",
  "encrypt": {
    "type": "luks",
    "version": "1",
    "passphrase": "secret123"
  }
}
```

### VeraCrypt (full-disk)

Add an `encrypt` block at the disk level.

```json
{
  "name": "encrypted-disk",
  "type": "GPT",
  "size": "512M",
  "encrypt": {
    "type": "veracrypt",
    "passphrase": "secret123"
  },
  "partitions": [
    {
      "number": 1,
      "type": "primary",
      "filesystem": "ext4",
      "size": "500M"
    }
  ]
}
```

---

## Examples

Example manifests and their output images are in the `examples/` directory:

| Example | Description |
|---------|-------------|
| `examples/example_gpt/` | GPT with FAT32, NTFS, exFAT, and ext3 partitions |
| `examples/example_mbr/` | MBR with primary + extended/logical partitions |
| `examples/example_luks/` | GPT with LUKS-encrypted ext4 partition |
| `examples/example_veracrypt/` | Full-disk VeraCrypt encryption |

---

## Testing

Run the full build + verification suite:

```bash
bash test/test.sh
```

This builds all 4 example images, then runs a verification pass that mounts every partition, checks file contents, and validates encryption with passphrase decryption.

---

## Basic Analysis of Images

Use **The Sleuthkit** and a hexeditor like **xxd** to view and analyze your newly created images.

### View the partition tables

```sh
# Partition tables for MBR and GPT
usename@hostname:/$ mmls examples/mbr_example/training_mbr.img

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

```

### View the first partition in both MBR and GPT images

```sh
# FAT32 partition for MBR and GPT
username@hostname:/$ fsstat -o 2048 examples/mbr_example/training_mbr.img

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
```

### Use a hexeditor to view the first 512 bytes of the MBR partition

```sh
# Use xxd to view the iamge data
username@hostname:/$ xxd -l 512 -g 1 examples/mbr_examples/training_mbr.img

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

---

## Project Structure

```
.
├── main.py              # CLI entry point
├── diskforge/         # Core Python modules
│   ├── builder.py       # Orchestrator
│   ├── disk.py          # Image creation and loop device management
│   ├── partitioning.py  # MBR/GPT partitioning and formatting
│   ├── populator.py     # File population (add/copy/move/delete)
│   ├── manifest.py      # Manifest loading and validation
│   └── utils.py         # Utility functions
├── examples/            # Example manifests and output
├── files/               # Sample files for populating images
├── test/                # Build and verification scripts
├── Dockerfile           # Container definition
└── docs/                # MkDocs documentation source
```

---

## To Do

- Add volume bootloader code
- Add basic operating system structures
- Investigate BitLocker support (requires Windows tooling)

---

## License

This project is open source and distributed under the MIT License.

> This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

---

## Author

Created by **Jacob Stauffer** | CISSP, GCFA, GREM, OSCP

Contributions and PRs welcome!

<a href="https://www.buymeacoffee.com/jstauffer" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
