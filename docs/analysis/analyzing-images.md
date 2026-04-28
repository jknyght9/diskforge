# Analyzing Images

Once you've built a disk image, you can analyze it with forensic tools. The Docker container includes Sleuth Kit, and you can also use tools on your host system.

---

## Viewing Partition Tables

Use `mmls` from Sleuth Kit to display the partition table:

=== "GPT"

    ```bash
    mmls training_gpt.img
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
    004:  000       0000002048   0000206847   0000204800   primary
    005:  001       0000206848   0000411647   0000204800   primary
    006:  002       0000411648   0000616447   0000204800   primary
    007:  003       0000616448   0000821247   0000204800   primary
    008:  -------   0000821248   0001048575   0000227328   Unallocated
    ```

=== "MBR"

    ```bash
    mmls training_mbr.img
    ```

    ```
    DOS Partition Table
    Offset Sector: 0
    Units are in 512-byte sectors

          Slot      Start        End          Length       Description
    000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
    001:  -------   0000000000   0000002047   0000002048   Unallocated
    002:  000:000   0000002048   0000206847   0000204800   Win95 FAT32 (0x0c)
    003:  000:001   0000206848   0000411647   0000204800   NTFS / exFAT (0x07)
    004:  000:002   0000411648   0000616447   0000204800   NTFS / exFAT (0x07)
    005:  Meta      0000616448   0000823295   0000206848   DOS Extended (0x05)
    008:  001:000   0000618496   0000823295   0000204800   Linux (0x83)
    ```

---

## Examining Filesystems

Use `fsstat` with the sector offset from `mmls`:

```bash
fsstat -o 2048 training_mbr.img
```

```
FILE SYSTEM INFORMATION
--------------------------------------------
File System Type: FAT32

OEM Name: mkfs.fat
Volume ID: 0x97f55ca5
Volume Label (Boot Sector): MBR_FAT32
Volume Label (Root Directory): MBR_FAT32
File System Type Label: FAT32
```

---

## Listing Files

Use `fls` to list files on a partition:

```bash
fls -o 2048 training_gpt.img
```

```
r/r 4:  doc1.docx
r/r 6:  copyofdocument1.docx
r/r 8:  zip1.zip
d/d 10: images
```

!!! tip
    Use `fls -r` for recursive listing, or `fls -d` to show deleted files only — useful for verifying that `delete_files` operations left recoverable artifacts.

---

## Hex Analysis

Use `xxd` to view raw bytes at specific offsets:

```bash
# View the MBR (first 512 bytes)
xxd -l 512 -g 1 training_mbr.img
```

The last two bytes should be `55 AA` — the MBR boot signature:

```
000001f0: ... 55 aa
```

For GPT disks, examine the GPT header at sector 1 (offset 512):

```bash
xxd -s 512 -l 512 -g 1 training_gpt.img
```

Look for the `EFI PART` signature at the start.

---

## Working with Encrypted Images

### LUKS

```bash
# Attach and map
losetup --find --show training_luks.img
kpartx -a /dev/loop0

# Check for LUKS
cryptsetup isLuks /dev/mapper/loop0p1

# View LUKS metadata
cryptsetup luksDump /dev/mapper/loop0p1

# Decrypt
echo -n "secret123" | cryptsetup open /dev/mapper/loop0p1 evidence
mount /dev/mapper/evidence /mnt/evidence
```

### VeraCrypt

```bash
veracrypt --text --mount training_veracrypt.img /mnt/evidence \
  --password "secret123" --pim 0 --keyfiles "" --non-interactive
```

---

## Tools Reference

| Tool | Command | Purpose |
|------|---------|---------|
| `mmls` | `mmls image.img` | Display partition table |
| `fsstat` | `fsstat -o OFFSET image.img` | Filesystem metadata |
| `fls` | `fls -o OFFSET image.img` | List files (including deleted) |
| `icat` | `icat -o OFFSET image.img INODE` | Extract file by inode |
| `xxd` | `xxd -l LENGTH image.img` | Hex dump |
| `cryptsetup` | `cryptsetup luksDump DEVICE` | LUKS header info |
| `veracrypt` | `veracrypt --text --mount ...` | VeraCrypt decrypt |
