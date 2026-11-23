![DiskForge](./media/diskforge.png)

# DiskForge

**DiskForge** is a Python-based tool for generating partitioned and encrypted disk images for digital forensics training, incident response simulations, CTF challenges, and lab environments.

Define disk layouts, filesystems, encryption, OS templates, and file population rules in a JSON manifest, then build reproducible disk images with a single Docker command.

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
- Unallocated space injection (hide passwords, recovery keys, artifacts)
- Filesystem countermeasures: hide directory entries on FAT32, exFAT, and NTFS
- AI analysis watermark: notice and canary GUID telling LLMs not to analyze the image
- MCP server: validate and build manifests from Claude or any MCP client
- File population with add, copy, move, and delete operations
- Wildcard and glob pattern support for file operations
- Multi-disk builds from a single manifest
- Automated test and verification suite (172 build checks + 15 MCP checks)
- Dockerized and reproducible (amd64 + arm64)

---

## Quick Start

### 1. Get the image

Pull the published image (amd64 + arm64) and tag it `diskforge`:

```bash
docker pull ghcr.io/jknyght9/diskforge:latest
docker tag ghcr.io/jknyght9/diskforge:latest diskforge
```

Or clone and build it yourself:

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

Templates create directories and forensic-relevant stub files (registry hives, log paths, system binaries). Custom templates are JSON files; see [Template Docs](https://jknyght9.github.io/diskforge/configuration/templates/).

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

Disks with no partition table, with the filesystem written directly to the device:

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
| `examples/example_btrfs/` | btrfs with Linux template |
| `examples/example_f2fs/` | F2FS filesystem |
| `examples/example_inject/` | Hidden data in unallocated space |
| `examples/example_countermeasures/` | Hidden directory entries on FAT32, exFAT, and NTFS |
| `examples/example_watermark/` | AI analysis notice on GPT (with NOTICE.txt) and MBR disks |

---

## Testing

```bash
bash test/test.sh
mcp_server/.venv/bin/python test/test_mcp.py   # MCP server checks (see docs/usage/mcp.md)
```

`test.sh` builds all 11 example scenarios, then runs 172 verification checks: partition tables, file contents, encryption passphrase validation (correct + wrong), boot code, template directories and stub files, unallocated injection, hidden directory entries (mount, raw bytes, TSK, `ntfsfix`), and watermark placement. `test_mcp.py` drives the MCP server through a real client and runs 15 checks, including a full build.

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
│   ├── injector.py      # Unallocated space injection
│   ├── countermeasures.py # FAT/exFAT/NTFS directory entry hiding
│   ├── watermark.py     # AI analysis notice and canary GUID
│   ├── manifest.py      # Manifest loading and validation
│   └── utils.py         # Utility functions
├── mcp_server/          # MCP server (validate and build through Docker)
├── templates/           # OS directory structure templates (JSON)
├── examples/            # Example manifests
├── files/               # Sample files for populating images
├── test/                # Build and verification scripts
├── docs/                # MkDocs documentation source
└── Dockerfile           # Container definition
```

---

## MCP Server

Validate and build manifests from Claude Code, Claude Desktop, or any MCP client. The server runs on the host and starts the `diskforge` image for each call. It builds images only; it has no tools for analyzing them.

```bash
python3 -m venv mcp_server/.venv && mcp_server/.venv/bin/pip install -e mcp_server
claude mcp add diskforge -- "$(pwd)/mcp_server/.venv/bin/python" "$(pwd)/mcp_server/server.py"
```

Tools: `validate_manifest`, `build`, `list_templates`, `list_examples`. See [MCP Server Docs](https://jknyght9.github.io/diskforge/usage/mcp/).

---

## Requirements

- Docker (Desktop or Engine)
- Python 3.10+ (MCP server only)
- `--privileged` flag required for loop device and partition operations

---

## To Do

- ZFS support (complex packaging: kernel module + userspace tools)
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
