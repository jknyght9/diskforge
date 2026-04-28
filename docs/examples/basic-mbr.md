# Example: MBR Disk

An MBR disk image demonstrating primary partitions, an extended partition, and a logical partition.

---

## Manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training_mbr",
      "label": "MBRExample",
      "type": "MBR",
      "size": "512M",
      "bootable": true,
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "fat32",
          "label": "MBR_FAT32",
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
          "label": "MBR_NTFS",
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
          "label": "MBR_EXFAT",
          "size": "100M",
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/text1.txt"]
          }
        },
        {
          "number": 4,
          "type": "extended",
          "filesystem": "",
          "size": "100M",
          "partitions": [
            {
              "number": 5,
              "type": "primary",
              "filesystem": "ext3",
              "label": "MBR_EXT3",
              "size": "100M",
              "populate": {
                "add_files": [{ "source": "/files/*", "target": "/" }]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_mbr:/output" \
  -v "$(pwd)/examples/example_mbr/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

## Verify

```bash
mmls examples/example_mbr/training_mbr.img
```

```
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
002:  000:000   0000002048   0000206847   0000204800   Win95 FAT32 (0x0c)
003:  000:001   0000206848   0000411647   0000204800   NTFS / exFAT (0x07)
004:  000:002   0000411648   0000616447   0000204800   NTFS / exFAT (0x07)
005:  Meta      0000616448   0000823295   0000206848   DOS Extended (0x05)
008:  001:000   0000618496   0000823295   0000204800   Linux (0x83)
```

## What Students Learn

- Understanding MBR partition table structure (4 primary slots max)
- Extended and logical partition concepts
- MBR type codes (0x0c = FAT32, 0x07 = NTFS/exFAT, 0x83 = Linux)
- The 2048-sector gap before the first logical partition inside the extended partition
