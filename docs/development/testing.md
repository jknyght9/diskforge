# Testing

DiskForge includes a two-phase test suite: **build** all example images, then **verify** them.

---

## Running the Full Suite

```bash
bash test/test.sh
```

This runs both phases automatically.

---

## Phase 1: Build

Builds all four example scenarios inside Docker:

| Scenario | Partition Table | Encryption | Filesystems |
|----------|----------------|------------|-------------|
| `example_gpt` | GPT | None | FAT32, NTFS, exFAT, ext3 |
| `example_mbr` | MBR | None | FAT32, NTFS, exFAT, ext3 (logical) |
| `example_luks` | GPT | LUKS v1 | ext4 |
| `example_veracrypt` | GPT | VeraCrypt | ext4 |

Each scenario runs a full `docker run` with the example's manifest and source files.

---

## Phase 2: Verify

A second container mounts all four built images and runs automated checks:

### What's Verified

**For all images:**

- Partition table is readable via `mmls`
- Each partition mounts successfully with the correct filesystem
- Expected files exist (`doc1.docx`, `copyofdocument1.docx`, `zip1.zip`, `images/pic1.jpg`)
- Deleted files are absent (`text1.txt`)

**For LUKS:**

- LUKS header is detected with `cryptsetup isLuks`
- Correct passphrase decrypts successfully
- Wrong passphrase is rejected
- Files are accessible after decryption

**For VeraCrypt:**

- Correct passphrase mounts successfully
- Wrong passphrase is rejected
- Files are accessible after decryption

### Expected Output

```
==========================================
 RESULTS
==========================================
  Total:  55
  Passed: 55
  Failed: 0
==========================================
```

---

## Running Individual Scenarios

To build a single scenario:

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_luks:/output" \
  -v "$(pwd)/examples/example_luks/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

To run just the verification on already-built images:

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_gpt:/output/example_gpt" \
  -v "$(pwd)/examples/example_mbr:/output/example_mbr" \
  -v "$(pwd)/examples/example_luks:/output/example_luks" \
  -v "$(pwd)/examples/example_veracrypt:/output/example_veracrypt" \
  -v "$(pwd)/test/verify.sh:/verify.sh" \
  --entrypoint bash \
  diskforge /verify.sh
```

---

## Adding New Test Scenarios

1. Create a new directory under `examples/` with a `manifest.json`
2. Add the scenario name to the `for` loop in `test/test.sh`
3. Add verification checks to `test/verify.sh`
