# DiskForge

**DiskForge** is a Python-based tool for generating partitioned and encrypted disk images for digital forensics training, incident response simulations, CTF challenges, and lab environments.

Define disk layouts, filesystems, encryption, OS templates, and file population rules in a JSON manifest — then build reproducible disk images with a single Docker command.

**[Full Documentation](https://jknyght9.github.io/diskforge)**

---

## Features

- MBR, GPT, and RAW (superfloppy) partition table support
- Primary, extended, and logical partitions
- Multiple filesystems: FAT32, NTFS, EXT2/3/4, XFS, exFAT, btrfs, F2FS, HFS+
- LUKS encryption (v1/v2) at the partition level
- VeraCrypt full-disk encryption
- MBR boot code (generic stub or custom binary)
- OS directory templates: Windows 10, Windows XP, Linux, macOS
- File population with add, copy, move, and delete operations
- Wildcard and glob pattern support for file operations
- Multi-disk builds from a single manifest
- Automated test and verification suite (78 checks)
- Dockerized and reproducible (amd64 + arm64)

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
          "filesystem": "ntfs",
          "label": "EVIDENCE",
          "size": "500M",
          "populate": {
            "template": "windows10",
            "add_files": [
              { "source": "/files/evtx/*", "target": "/Windows/System32/winevt/Logs" },
              { "source": "/files/docs/*", "target": "/Users/Default/Documents" }
            ],
            "delete_files": ["/Users/Default/Documents/secret.xlsx"]
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

## OS Templates

Apply realistic directory structures before populating with evidence files:

```json
"populate": {
  "template": "windows10",
  "add_files": [{ "source": "/files/*", "target": "/Users/Default/Documents" }]
}
```

| Template | OS | Recommended FS | Key Structures |
|----------|----|---------------|----------------|
| `windows10` | Windows 10/11 | NTFS | System32, winevt, Prefetch, registry hives, $Recycle.Bin |
| `windowsxp` | Windows XP | NTFS | WINDOWS, Documents and Settings, Recycled, ntldr |
| `linux` | Linux | ext4 | FHS layout, /var/log, /etc, /home, cron, SSH |
| `macos` | macOS | HFS+ | /Library, /System, LaunchAgents, FSEvents, Spotlight |

Templates create directories and forensic-relevant stub files (registry hives, log paths, system binaries). Custom templates are JSON files — see [Template Docs](https://jknyght9.github.io/diskforge/configuration/templates/).

---

## Encryption

### LUKS (partition-level)

```json
"encrypt": {
  "type": "luks",
  "version": "1",
  "passphrase": "secret123"
}
```

Supported on ext2/3/4 and xfs filesystems.

### VeraCrypt (full-disk)

```json
"encrypt": {
  "type": "veracrypt",
  "passphrase": "secret123"
}
```

Placed at the disk level, not the partition level.

---

## RAW Disks (Superfloppy)

Disks with no partition table — filesystem written directly to the device:

```json
{
  "name": "floppy",
  "type": "RAW",
  "size": "1.44M",
  "filesystem": "fat32",
  "label": "FLOPPY",
  "populate": {
    "add_files": [{ "source": "/files/*", "target": "/" }]
  }
}
```

---

## Examples

| Example | Description |
|---------|-------------|
| `examples/example_gpt/` | GPT with FAT32, NTFS, exFAT, and ext3 partitions |
| `examples/example_mbr/` | MBR with boot code, primary + extended/logical partitions |
| `examples/example_luks/` | GPT with LUKS-encrypted ext4 partition |
| `examples/example_veracrypt/` | Full-disk VeraCrypt encryption |
| `examples/example_raw/` | RAW superfloppy FAT32 image |
| `examples/example_template/` | Windows 10 OS template with NTFS |

---

## Testing

```bash
bash test/test.sh
```

Builds all 6 example images, then runs 78 verification checks: partition tables, file contents, encryption passphrase validation (correct + wrong), boot code, template directories, and stub files.

---

## Project Structure

```
.
├── main.py              # CLI entry point
├── diskforge/           # Core Python modules
│   ├── builder.py       # Orchestrator
│   ├── disk.py          # Image creation, loop devices, VeraCrypt, RAW
│   ├── partitioning.py  # MBR/GPT partitioning, formatting, boot code
│   ├── populator.py     # File population (template/add/copy/move/delete)
│   ├── templates.py     # OS template loader and applicator
│   ├── manifest.py      # Manifest loading and validation
│   └── utils.py         # Utility functions
├── templates/           # OS directory structure templates (JSON)
├── examples/            # Example manifests
├── files/               # Sample files for populating images
├── test/                # Build and verification scripts
├── docs/                # MkDocs documentation source
└── Dockerfile           # Container definition
```

---

## To Do

- ZFS support (complex packaging — kernel module + userspace tools)
- Investigate BitLocker support (requires Windows tooling)
- APFS support (no Linux implementation exists)

---

## License

This project is open source and distributed under the MIT License.

> This software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

---

## Author

Created by **Jacob Stauffer** | CISSP, GCFA, GREM, OSCP

Contributions and PRs welcome!

<a href="https://www.buymeacoffee.com/jstauffer" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>
