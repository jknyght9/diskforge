# Supported Filesystems

DiskForge supports the following filesystems for partition formatting.

---

## Filesystem Support Matrix

| Filesystem | MBR Type Code | LUKS Compatible | VeraCrypt Compatible | Tool Used |
|------------|---------------|-----------------|---------------------|-----------|
| **FAT32** | `0x0c` | No | Yes | `mkfs.vfat -F32` |
| **NTFS** | `0x07` | No | Yes | `mkfs.ntfs` |
| **ext2** | `0x83` | Yes | Yes | `mkfs.ext2` |
| **ext3** | `0x83` | Yes | Yes | `mkfs.ext3` |
| **ext4** | `0x83` | Yes | Yes | `mkfs.ext4` |
| **XFS** | `0x83` | Yes | Yes | `mkfs.xfs` |
| **exFAT** | `0x07` | No | No | `mkfs.exfat` |
| **HFS+** | `0xAF` | No | No | `mkfs.hfsplus` |

---

## Filesystem Details

### FAT32

- Maximum file size: 4 GB
- No file permissions or ownership
- Widely compatible (USB drives, SD cards, Windows/macOS/Linux)
- Common in forensics: USB evidence, camera cards

### NTFS

- Windows native filesystem
- Supports file permissions, alternate data streams (ADS), journaling
- Forensically rich: `$MFT`, `$LogFile`, `$UsnJrnl`
- Mounted via `ntfs-3g` in the container

### ext2 / ext3 / ext4

- Linux native filesystems
- ext2: no journaling (good for teaching raw filesystem concepts)
- ext3: adds journaling
- ext4: adds extents, larger volume support
- **Only filesystems supported with LUKS encryption**

### XFS

- High-performance Linux filesystem
- Supports LUKS encryption
- Used in enterprise Linux distributions (RHEL/CentOS default)

### exFAT

- Extended FAT format, no 4GB file limit
- No journaling, no permissions
- Mounted via `mount.exfat-fuse` in the container

### HFS+

- macOS native filesystem (pre-APFS)
- Supports resource forks, file permissions, journaling
- Forensically relevant: `.fseventsd`, `.Spotlight-V100`, `.Trashes`
- Formatted via `mkfs.hfsplus` (from `hfsprogs` package)
- Use with the `macos` OS template for realistic macOS forensic scenarios

!!! note "APFS Not Supported"
    APFS (Apple File System) has no Linux implementation and cannot be created by DiskForge. Use HFS+ for macOS forensic training scenarios.

!!! warning "exFAT Limitations"
    exFAT is mounted using FUSE (`exfat-fuse`) inside the container, which can be slower than kernel-native mounts. It does not support LUKS or VeraCrypt encryption within DiskForge.

---

## Choosing a Filesystem

=== "Forensics Training"

    | Goal | Recommended Filesystem |
    |------|----------------------|
    | File recovery basics | FAT32 (simple structure) |
    | Windows forensics | NTFS (rich metadata) |
    | Linux forensics | ext4 |
    | Encrypted evidence | ext4 + LUKS |
    | USB/removable media | FAT32 or exFAT |

=== "Partition Table Pairing"

    | Partition Table | Common Pairings |
    |----------------|-----------------|
    | MBR | FAT32, NTFS (Windows-style) |
    | GPT | ext4, XFS (Linux-style) |
    | Either | Any supported filesystem |
