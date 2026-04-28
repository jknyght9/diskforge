# Manifest Reference

The manifest is a JSON file that defines one or more disk images to build. Each disk specifies its partition table type, size, partitions, encryption, and file population rules.

---

## Top-Level Structure

```json
{
  "schema_version": "1.0",
  "disks": [ ... ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | No | Manifest version (currently `"1.0"`) |
| `disks` | array | Yes | Array of disk definitions |

---

## Disk Object

```json
{
  "name": "disk-name",
  "type": "GPT",
  "size": "512M",
  "label": "MyDisk",
  "bootable": true,
  "encrypt": { ... },
  "partitions": [ ... ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Image filename (produces `{name}.img`) |
| `type` | string | Yes | Partition table type: `"MBR"` or `"GPT"` |
| `size` | string | Yes | Disk size (e.g. `"512M"`, `"32G"`) |
| `label` | string | No | Disk label |
| `bootable` | boolean | No | Mark disk as bootable |
| `encrypt` | object | No | Disk-level encryption (VeraCrypt only) |
| `partitions` | array | Yes | Array of partition definitions |

---

## Partition Object

```json
{
  "number": 1,
  "type": "primary",
  "filesystem": "ext4",
  "label": "DATA",
  "size": "500M",
  "bootable": true,
  "encrypt": { ... },
  "populate": { ... }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `number` | integer | Yes | Partition number (1-based) |
| `type` | string | Yes | `"primary"` or `"extended"` (MBR only) |
| `filesystem` | string | Yes | Filesystem type (see [Supported Filesystems](../reference/filesystems.md)) |
| `label` | string | No | Filesystem/partition label |
| `size` | string | Yes | Partition size (e.g. `"100M"`, `"50G"`) |
| `bootable` | boolean | No | Mark partition as bootable |
| `encrypt` | object | No | Partition-level encryption (LUKS only) |
| `populate` | object | No | File population rules |

### Extended Partitions (MBR Only)

Extended partitions contain nested logical partitions:

```json
{
  "number": 4,
  "type": "extended",
  "filesystem": "",
  "size": "200M",
  "partitions": [
    {
      "number": 5,
      "type": "primary",
      "filesystem": "ext3",
      "label": "LOGICAL1",
      "size": "200M"
    }
  ]
}
```

!!! note
    Extended partitions cannot have encryption applied directly. Encrypt the logical partitions inside them instead.

---

## Encryption Object

See the [Encryption Guide](encryption.md) for detailed configuration.

=== "LUKS (Partition-Level)"

    ```json
    "encrypt": {
      "type": "luks",
      "version": "1",
      "passphrase": "secret123"
    }
    ```

    | Field | Type | Required | Description |
    |-------|------|----------|-------------|
    | `type` | string | Yes | `"luks"` |
    | `version` | string | No | `"1"` (default) or `"2"` |
    | `passphrase` | string | Yes | Decryption passphrase |

=== "VeraCrypt (Disk-Level)"

    ```json
    "encrypt": {
      "type": "veracrypt",
      "passphrase": "secret123"
    }
    ```

    | Field | Type | Required | Description |
    |-------|------|----------|-------------|
    | `type` | string | Yes | `"veracrypt"` |
    | `passphrase` | string | Yes | Decryption passphrase |

---

## Populate Object

The `populate` block controls file operations on a partition. Operations execute in order: add → copy → move → delete.

```json
"populate": {
  "add_files": [ ... ],
  "copy_files": [ ... ],
  "move_files": [ ... ],
  "delete_files": [ ... ]
}
```

### add_files

Copy files from the host (`/files/` mount) into the partition.

```json
"add_files": [
  { "source": "/files/*", "target": "/" },
  { "source": "/files/images/*", "target": "/Pictures" }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Glob pattern for source files (host path) |
| `target` | string | Target directory inside the partition |

!!! tip
    The `source` field supports glob patterns. `/files/*` matches all files and directories in `/files/`. Nested patterns like `/files/**/*.jpg` work too.

### copy_files

Duplicate files within the partition.

```json
"copy_files": [
  { "source": "/document.docx", "target": "/backup/document.docx" }
]
```

### move_files

Relocate files within the partition.

```json
"move_files": [
  { "source": "/temp/report.pdf", "target": "/final/report.pdf" }
]
```

### delete_files

Remove files or directories. Supports wildcards.

```json
"delete_files": [
  "/text1.txt",
  "/temp/*"
]
```

!!! info "Forensic Training Tip"
    Deleted files leave recoverable artifacts on the filesystem. Use `delete_files` to create recovery exercises for students — the files were written to disk before deletion.
