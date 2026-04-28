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
