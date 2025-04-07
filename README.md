# DiskBuilder

**DiskBuilder** is a flexible Python-based tool for generating partitioned disk images (MBR and GPT) for use in digital forensics training, incident response simulations, lab environments, or automated system provisioning.

It uses a JSON manifest to define disk layouts, filesystems, population rules (add, delete, move), and bootable flags. It supports building and populating multiple disk images at once using a containerized workflow.

---

## Features

- ✅ MBR and GPT partition table support
- ✅ Primary, extended, and logical partitions
- ✅ Multiple filesystem formats: `FAT32`, `NTFS`, `EXT2/3/4`, `XFS`, `EXFAT`
- ✅ Populate files into partitions
- ✅ Delete files or directories (with wildcard support)
- ✅ Move files after population
- ✅ Build multiple disk images from a single manifest
- ✅ Dockerized and reproducible

---

## Use Cases

- Digital forensics labs (e.g., deleted file recovery)
- Simulated data breach or whistleblower scenarios
- Disk images for malware analysis or CTF challenges
- Teaching filesystem and partition concepts

---

## Examples

You can find real-world examples of manifest files in the examples/ folder.

- examples/mbr_example/manifest.json: MBR image with FAT32, NTFS, exFAT, and XFS partitions
- examples/gpt_example/manifest.json: GPT image with FAT32, NTFS, exFAT, and XFS partitions

---

## 🐳 Docker Requirements

This tool uses loopback devices and requires `--privileged` mode when running Docker.

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/your-org/diskbuilder.git
cd diskbuilder
```

### 2. Add your files

Place files to embed inside disk images in the `files/` directory.

```
files/
├── text1.txt
├── Contracts/
│   └── Vendor_Contract.docx
└── Notes/
    └── password_list.txt
```

### 3. Define your disk layout in `manifest.json`

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "usb-training",
      "type": "MBR",
      "size": "512M",
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "fat32",
          "size": "100M",
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "move_files": [
              {
                "source": "/Contracts/Vendor_Contract.docx",
                "target": "/Vendor.docx"
              }
            ],
            "delete_files": ["/Notes/*"]
          }
        }
      ]
    }
  ]
}
```

### 4. Build with Docker

```bash
docker build -t disk-builder .
docker run --rm --privileged \
  -v "$(pwd)/manifest.json:/app/manifest.json" \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/output:/output" \
  disk-builder manifest.json
```

Output `.img` files will be placed in the `output/` directory.

---

## Manifest Structure

Each disk entry must include:

```json
{
  "name": "disk-name",
  "type": "MBR|GPT",
  "size": "512M|32G|...",
  "bootable": false,
  "partitions": [ ... ]
}
```

Each partition may include:

- `filesystem`: One of `fat32`, `ntfs`, `ext2`, `ext3`, `ext4`, `xfs`, `exfat`
- `populate`:
  - `add_files`: Copy files from host into image
  - `move_files`: Move populated files to new locations within the image
  - `delete_files`: Remove files or directories, with `*` wildcard support

---

## 📁 Folder Structure

```
.
├── files/           # Files to include in images
├── output/          # Resulting disk images
├── manifest.json    # Disk layout and population manifest
├── Dockerfile
├── main.py
├── diskbuilder/     # Core Python source files
└── examples/        # Example manifest templates
```

---

## Analyzing Images

Use **The Sleuthkit** and a hexeditor like **xxd** to view and analyze your newly created images.

### View the partition tables.

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

### View the first partition in both MBR and GPT images.

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

### Use a hexeditor to view the first 512 bytes of the MBR partition.

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

## ⚖️ Legal / License

This project is open source and distributed under the MIT License.

> This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

---

## 👨‍💻 Author

Created by Jacob Stauffer | CISSP, GCFA, GREM, OSCP — Contributions and PRs welcome!

<a href="https://www.buymeacoffee.com/jstauffer" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
