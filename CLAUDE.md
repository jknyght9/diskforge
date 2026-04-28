# DiskForge

Digital forensics training tool that builds disk images from JSON manifests. Runs inside a privileged Docker container (Debian Bullseye).

## Architecture

- `main.py` — CLI entry point, takes manifest path as argument
- `diskforge/builder.py` — Orchestrator: cleanup, load manifest, iterate disks
- `diskforge/disk.py` — DiskImage class: create image, attach loop device, delegate partitioning/populating
- `diskforge/partitioning.py` — Partition tables (MBR via sfdisk, GPT via parted) and filesystem formatting (LUKS, VeraCrypt, standard mkfs)
- `diskforge/populator.py` — Mount, add/copy/move/delete files, unmount, close encryption
- `diskforge/manifest.py` — JSON manifest loader and validator
- `diskforge/utils.py` — `fail()` and `wait_for_device()` helpers

## Key concepts

- Manifests define disks with partition tables, filesystems, encryption, and file population rules
- Encryption: LUKS (partition-level, ext2/3/4/xfs only) and VeraCrypt (full-disk only)
- Runs in Docker with `--privileged` for loop devices, kpartx, cryptsetup, veracrypt
- Volume mounts: `/files` (source files), `/manifests` (manifest JSON), `/output` (built images)

## Build & run

```bash
docker build -t disk-builder .
docker run --rm --privileged \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/output:/output" \
  disk-builder /manifests/manifest.json
```

## Test

```bash
bash test/test.sh  # builds all 4 example scenarios
```
