# Example: RAW Disk (Superfloppy)

A raw disk image with no partition table — the filesystem is written directly to the device.

---

## Manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training_raw",
      "label": "RAWDISK",
      "type": "RAW",
      "size": "64M",
      "filesystem": "fat32",
      "populate": {
        "add_files": [{ "source": "/files/*", "target": "/" }],
        "delete_files": ["/text1.txt"]
      }
    }
  ]
}
```

!!! note
    RAW disks have no `partitions` array. The `filesystem` and `populate` fields go directly on the disk object.

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_raw:/output" \
  -v "$(pwd)/examples/example_raw/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

## Verify

```bash
# mmls will NOT find a partition table (expected)
mmls training_raw.img
# Error: unable to find partition table

# Use fsstat directly on the image (no offset needed)
fsstat training_raw.img
```

```
FILE SYSTEM INFORMATION
--------------------------------------------
File System Type: FAT32
```

## What Students Learn

- Recognizing a disk image without a partition table (superfloppy format)
- Understanding that `mmls` failing doesn't mean the image is corrupted
- Using `fsstat` directly on a raw image vs. with a sector offset
- Common in USB thumb drives and floppy disk forensics
