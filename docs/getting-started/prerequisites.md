# Prerequisites

## Requirements

| Requirement | Details |
|-------------|---------|
| **Docker** | Docker Desktop or Docker Engine with BuildKit |
| **Privileged mode** | Required for loop devices, device-mapper, and cryptsetup |
| **Platform** | Linux or macOS (via Docker Desktop) |
| **Architecture** | amd64 or arm64 |

!!! warning "Privileged Mode Required"
    DiskForge uses loopback devices, `kpartx`, `cryptsetup`, and `veracrypt` inside the container. The `--privileged` flag is **required** for Docker runs. This gives the container full access to the host's device subsystem.

## What's Inside the Container

The Docker image (Debian Bullseye) includes:

| Tool | Purpose |
|------|---------|
| `parted` / `sfdisk` / `fdisk` | Partition table creation |
| `mkfs.*` (vfat, ntfs, ext2/3/4, xfs, exfat) | Filesystem formatting |
| `kpartx` | Partition-to-device mapping for loop devices |
| `cryptsetup` | LUKS encryption |
| `veracrypt` (CLI) | VeraCrypt encryption |
| `sleuthkit` | Forensic analysis (`mmls`, `fsstat`, `fls`) |
| `python3` | Runtime for diskforge |

## No Host Dependencies

Everything runs inside Docker — you don't need to install any forensic tools, cryptsetup, or veracrypt on your host machine. Just Docker.
