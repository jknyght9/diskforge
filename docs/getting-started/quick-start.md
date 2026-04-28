# Quick Start

Build your first forensic disk image in under 5 minutes.

---

## 1. Clone the Repository

```bash
git clone https://github.com/jknyght9/diskforge.git
cd diskforge
```

## 2. Build the Docker Image

```bash
docker build -t diskforge .
```

## 3. Add Source Files

Place files you want to embed in disk images in the `files/` directory:

```
files/
├── text1.txt
├── doc1.docx
├── zip1.zip
└── images/
    └── pic1.jpg
```

These files are mounted into the container at `/files/` and referenced in your manifest with paths like `/files/*`.

## 4. Create a Manifest

Create a `manifest.json` defining your disk layout:

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "my-first-disk",
      "type": "GPT",
      "size": "512M",
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "fat32",
          "label": "EVIDENCE",
          "size": "500M",
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

## 5. Build the Image

```bash
docker run --rm --privileged \
  -v "$(pwd)/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/output:/output" \
  diskforge /manifests/manifest.json
```

## 6. Verify the Output

Your disk image is in `output/my-first-disk.img`. Analyze it with Sleuth Kit:

```bash
mmls output/my-first-disk.img
```

```
GUID Partition Table (EFI)
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Safety Table
001:  -------   0000000000   0000002047   0000002048   Unallocated
002:  Meta      0000000001   0000000001   0000000001   GPT Header
003:  Meta      0000000002   0000000033   0000000032   Partition Table
004:  000       0000002048   0001026047   0001024000   primary
```

---

## Scenarios

For real-world training scenarios (multi-disk, encrypted evidence, capstone exercises), keep scenario files in a separate private repository alongside DiskForge:

```
current/
├── diskforge/                # Public tool (this repo)
└── diskforge-scenarios/      # Private scenarios
    ├── is4483-capstone/
    │   ├── manifest.json
    │   ├── files/
    │   └── output/
    └── my-scenario/
        ├── manifest.json
        ├── files/
        └── output/
```

Build a scenario from the diskforge directory:

```bash
SCENARIO=../diskforge-scenarios/my-scenario

docker run --rm --privileged \
  -v "$(pwd -P)/$SCENARIO/output:/output" \
  -v "$(pwd -P)/$SCENARIO/manifest.json:/manifests/manifest.json" \
  -v "$(pwd -P)/$SCENARIO/files:/files" \
  diskforge /manifests/manifest.json
```

This keeps answer keys, evidence files, and passphrases private while the tool stays public.

---

## Next Steps

- [:octicons-arrow-right-24: Manifest Reference](../configuration/manifest-reference.md) — full manifest field documentation
- [:octicons-arrow-right-24: Encryption Guide](../configuration/encryption.md) — add LUKS or VeraCrypt encryption
- [:octicons-arrow-right-24: Examples](../examples/basic-gpt.md) — browse complete example manifests
