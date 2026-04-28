# Example: VeraCrypt Encryption

A full-disk VeraCrypt-encrypted image with an ext4 filesystem inside.

---

## Manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training_veracrypt",
      "label": "VERAExample",
      "type": "GPT",
      "size": "512M",
      "bootable": true,
      "encrypt": {
        "type": "veracrypt",
        "passphrase": "secret123"
      },
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "ext4",
          "label": "VERA_EXT4",
          "size": "500M",
          "bootable": true,
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

!!! warning "Disk-Level Encryption"
    The `encrypt` block is on the **disk**, not the partition. VeraCrypt encrypts the entire disk image. Only one partition is supported inside a VeraCrypt-encrypted disk.

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_veracrypt:/output" \
  -v "$(pwd)/examples/example_veracrypt/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

## Analysis Walkthrough

### 1. Initial Examination

```bash
mmls examples/example_veracrypt/training_veracrypt.img
```

With full-disk VeraCrypt encryption, `mmls` will **not** show a recognizable partition table — the entire disk appears as random data. This is by design.

```bash
xxd -l 64 training_veracrypt.img
```

The first bytes show no recognizable filesystem or partition signatures — just encrypted data.

### 2. Identify as Encrypted

VeraCrypt volumes don't have obvious headers like LUKS. Forensic indicators include:

- No recognizable partition table or filesystem signatures
- High entropy throughout the entire image
- File size matches common disk sizes (power-of-2 aligned)

### 3. Decrypt and Mount

```bash
veracrypt --text --mount training_veracrypt.img /mnt/evidence \
  --password "secret123" --pim 0 --keyfiles "" --non-interactive
```

### 4. Browse the Contents

```bash
ls /mnt/evidence
```

### 5. Dismount

```bash
veracrypt --text --dismount training_veracrypt.img
```

## What Students Learn

- VeraCrypt full-disk encryption hides all partition and filesystem structures
- No detectable header (unlike LUKS) — makes identification harder
- High-entropy analysis can suggest encryption
- VeraCrypt requires the correct passphrase, PIM, and keyfiles to decrypt
- Contrast with LUKS: VeraCrypt is designed for plausible deniability
