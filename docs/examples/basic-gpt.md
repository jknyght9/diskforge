# Example: GPT Disk

A basic GPT disk image with four partitions demonstrating different filesystems.

---

## Manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training_gpt",
      "label": "GPTExample",
      "type": "GPT",
      "size": "512M",
      "bootable": true,
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "fat32",
          "label": "GPT_FAT32",
          "size": "100M",
          "bootable": true,
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/text1.txt"]
          }
        },
        {
          "number": 2,
          "type": "primary",
          "filesystem": "ntfs",
          "label": "GPT_NTFS",
          "size": "100M",
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/text1.txt"]
          }
        },
        {
          "number": 3,
          "type": "primary",
          "filesystem": "exfat",
          "label": "GPT_EXFAT",
          "size": "100M",
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/text1.txt"]
          }
        },
        {
          "number": 4,
          "type": "primary",
          "filesystem": "ext3",
          "label": "GPT_EXT3",
          "size": "100M",
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/text1.txt"]
          }
        }
      ]
    }
  ]
}
```

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_gpt:/output" \
  -v "$(pwd)/examples/example_gpt/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

## Verify

```bash
mmls examples/example_gpt/training_gpt.img
```

```
GUID Partition Table (EFI)
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
004:  000       0000002048   0000206847   0000204800   primary
005:  001       0000206848   0000411647   0000204800   primary
006:  002       0000411648   0000616447   0000204800   primary
007:  003       0000616448   0000821247   0000204800   primary
```

## What Students Learn

- Identifying GPT partition tables with `mmls`
- Recognizing different filesystem types at specific sector offsets
- Recovering deleted files (`text1.txt` was written then removed)
- Using `fsstat` to examine filesystem metadata for each partition type
