# DiskForge: filesystem countermeasures (design handoff, 2026-11-20)

## Request
Hide files on FAT and NTFS (exFAT if it works) as forensic-training countermeasures.
- FAT: zero root dir entries so the OS sees end-of-directory early.
- NTFS, one of two methods per directory:
  - `index_truncate`: shrink the index "bytes in use" so the hidden entries fall outside it.
  - `index_flag`: set the LAST_ENTRY flag (0x02) on an earlier entry.
- exFAT: use the FAT method if it works.

## Where it fits
- `builder.py` calls `image.inject()` after populating, and `injector.py` writes raw bytes after the build. Countermeasures follow the same pattern: a new module (`diskforge/countermeasures.py`) that edits raw bytes after unmount.
- Ordering constraint: for LUKS partitions the edit must happen on the mapped device after unmount but BEFORE `cryptsetup close`. That means a hook in `populator.py` between unmount and close, not after the build. Read populator.py and disk.py before deciding.
- Filesystems in use: `fat32` (mkfs.vfat -F32), `ntfs` (mkfs.ntfs), `exfat` (mkfs.exfat). FAT32 root is a cluster chain (no fixed FAT12/16 root region), so a "root dir" is just the root cluster chain.

## Proposed manifest shape (per partition, or per disk for RAW)
```json
"countermeasures": [
  {"type": "fat_dir_truncate", "path": "/", "hide": ["secret.txt", "plans.docx"]},
  {"type": "ntfs_index_flag", "path": "/", "hide": ["zz_secret.txt"]}
]
```
Validate in `manifest.py`: the type must match the partition's filesystem, and each NTFS directory gets only one NTFS method ("one or the other").

## FAT32 and exFAT mechanics
- Directory order on disk is insertion order. Write the hidden files LAST (after the normal add/copy steps), then set the first byte of the first hidden file's first entry to 0x00.
  - FAT32: the first entry is its first LFN entry (attribute 0x0F) if it has one, otherwise the 8.3 entry.
  - exFAT: the first entry is the File entry (type 0x85) that starts the entry set (0x85, 0xC0 stream, 0xC1 name).
- Everything after that byte stays intact on disk, so students can recover it by carving or with fls on a hex view. That is the training point.
- exFAT: the spec defines type 0x00 as end-of-directory, and the Linux exfat driver stops on it. The root also holds the bitmap (0x81), upcase (0x82) and label (0x83) entries first, so those stay visible. Expected to work. Verify by mounting (hidden files absent) and with fsck.exfat (should report it, which is fine).
- Hiding only the trailing files is inherent to this method: every entry after the cut is hidden too.

## NTFS mechanics
- Index entries are SORTED (by uppercased filename collation), not kept in insertion order. Hiding "everything after the cut" only hides chosen files if they sort after every visible file in that directory.
  - DECIDED (Jake, 2026-11-20): the manifest lists the files to hide. The tool validates that every hidden name sorts after every visible name in that directory and fails loud if not. Authors name hidden files so they sort last (e.g. `zz_secret.txt`).
- Small directories keep their index in `$INDEX_ROOT`, resident in the MFT record. Only larger ones use `$INDEX_ALLOCATION` / INDX records. Both use the same index node header (entries offset, bytes in use, allocated size), so support both.
- Multi-level B-trees: a cut inside one node also hides that node's subnodes. Recommended scope: single-node indexes only, and fail if the directory's index has subnodes.
- Fixups: MFT and INDX records carry update sequence arrays. Apply them on read and re-apply them on write, or the record gets corrupted.
- `index_flag`: set 0x02 on the cut entry. Parsers treat a LAST entry as keyless and stop, so it and everything after are hidden.
- `index_truncate`: UNCERTAIN. ntfs-3g and Windows walk entries until LAST_ENTRY and bounds-check against bytes in use. Shrinking the length without a valid terminating entry inside it may make the volume read as corrupt instead of hidden. A real end entry may need to be written at the new boundary. Prototype it and test with ntfs-3g mount, TSK `fls`, and ideally Windows.

## Verification (success criteria)
For each FS and method, run an example manifest in `examples/` plus `test/verify.sh` checks:
1. A normal mount does not list the hidden files.
2. The hidden filenames are still present in the raw directory or index bytes (recoverable).
3. The visible files still list and read correctly.
4. The image still mounts without error.
