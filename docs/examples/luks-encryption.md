# Example: LUKS Encryption

A GPT disk image with a LUKS-encrypted ext4 partition.

---

## Manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training_luks",
      "label": "LUKSExample",
      "type": "GPT",
      "size": "512M",
      "bootable": true,
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "ext4",
          "label": "LUKS_EXT4",
          "size": "500M",
          "bootable": true,
          "populate": {
            "add_files": [{ "source": "/files/*", "target": "/" }],
            "delete_files": ["/text1.txt"]
          },
          "encrypt": {
            "type": "luks",
            "passphrase": "secret123"
          }
        }
      ]
    }
  ]
}
```

!!! note
    The `encrypt` block is on the **partition**, not the disk. LUKS version defaults to `"1"` if not specified.

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_luks:/output" \
  -v "$(pwd)/examples/example_luks/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

## Analysis Walkthrough

### 1. Examine the Partition Table

```bash
mmls examples/example_luks/training_luks.img
```

```
GUID Partition Table (EFI)
      Slot      Start        End          Length       Description
004:  000       0000002048   0001026047   0001024000   primary
```

The partition table looks normal — LUKS encryption is invisible at this level.

### 2. Detect the LUKS Header

Attach the image and check the partition:

```bash
losetup --find --show training_luks.img
kpartx -a /dev/loop0
cryptsetup isLuks /dev/mapper/loop0p1 && echo "LUKS detected!"
```

### 3. Examine the LUKS Header

```bash
cryptsetup luksDump /dev/mapper/loop0p1
```

This reveals the LUKS version, cipher, hash, key slots, and other metadata useful for forensic analysis.

### 4. Decrypt and Mount

```bash
echo -n "secret123" | cryptsetup open /dev/mapper/loop0p1 evidence
mount /dev/mapper/evidence /mnt/evidence
ls /mnt/evidence
```

### 5. Clean Up

```bash
umount /mnt/evidence
cryptsetup close evidence
kpartx -d /dev/loop0
losetup -d /dev/loop0
```

## What Students Learn

- LUKS headers are detectable even without the passphrase
- `cryptsetup luksDump` reveals encryption metadata
- Partition tables don't reveal encryption — deeper analysis is needed
- Passphrase recovery/cracking is the key challenge in encrypted evidence
