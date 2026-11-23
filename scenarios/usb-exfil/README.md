# USB Exfiltration Scenario

A tutorial scenario where students examine a USB drive used to stage stolen data. Files were hidden with anti-forensics countermeasures, and the image carries an AI analysis watermark. It is the worked example for the DiskForge v1.3.0 Medium article.

## Scenario Narrative

An insider copied a financial ledger to a personal USB drive and uploaded it to Dropbox. Before handing the drive back, they hid their notes and the ledger by editing the directory structures directly, so a normal mount no longer lists either file.

## What Students Will Find

### Partition 1: USBDATA (FAT32, `fat_dir_zero`)
- `doc1.docx` is visible
- `transfer_notes.txt` is hidden: its directory entry was moved to the end of the root directory and its first byte zeroed. Windows, Linux, and TSK (`fls`, `fls -d`) all stop at the `0x00` byte, so the entry only shows up in a hex view of the raw directory clusters

### Partition 2: ARCHIVE (NTFS, `ntfs_index_truncate` in `/Documents`)
- `Documents/doc1.docx` and `Documents/text1.txt` are visible
- `Documents/zz_ledger.xlsx` is hidden: its index entry was pushed into `$I30` index slack. `fls -r` recovers the name as an unallocated entry (`-/r ... zz_ledger.xlsx`), and the MFT record and data are intact

### Unallocated Space
- `dropbox upload complete: zz_ledger.xlsx` right after the last partition

### AI Analysis Watermark
- Notice and canary GUID at sector 34, at the end of unallocated space, and in `NOTICE.txt` on both partitions (4 copies). The generated GUID is printed in the build log

## Build

```bash
docker pull ghcr.io/jknyght9/diskforge:1.3.0
docker run --rm --privileged \
  -v "$(pwd)/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/output:/output" \
  ghcr.io/jknyght9/diskforge:1.3.0 /manifests/manifest.json
```

Output: `output/usb_exfil.img` (256MB)

## Learning Objectives

- GPT partition analysis with `mmls`
- Spotting files hidden from a mounted filesystem
- Reading raw FAT directory entries in a hex editor
- Recovering NTFS index slack entries with `fls`
- Unallocated space analysis with `strings`/`blkls`
- Recognizing an AI analysis watermark and canary GUID
