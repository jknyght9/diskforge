#!/bin/bash
# Verification script for diskforge images
# Runs inside the Docker container to validate built images
set -euo pipefail

PASS=0
FAIL=0
TESTS=0

pass() {
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
    TESTS=$((TESTS + 1))
}

fail() {
    echo "  [FAIL] $1"
    FAIL=$((FAIL + 1))
    TESTS=$((TESTS + 1))
}

check() {
    local desc="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        pass "$desc"
    else
        fail "$desc"
    fi
}

check_file_on_mount() {
    local mount_point="$1"
    local file="$2"
    if [ -f "$mount_point/$file" ]; then
        pass "Found $file"
    else
        fail "Missing $file"
    fi
}

check_file_absent() {
    local mount_point="$1"
    local file="$2"
    if [ ! -f "$mount_point/$file" ]; then
        pass "$file was deleted (not present)"
    else
        fail "$file should have been deleted but exists"
    fi
}

# Expected files (from /files/* minus text1.txt which gets deleted)
EXPECTED_FILES="doc1.docx copyofdocument1.docx zip1.zip images/pic1.jpg"
DELETED_FILE="text1.txt"

verify_files() {
    local mount_point="$1"
    for f in $EXPECTED_FILES; do
        check_file_on_mount "$mount_point" "$f"
    done
    check_file_absent "$mount_point" "$DELETED_FILE"
}

cleanup_mount() {
    local mount_point="$1"
    umount "$mount_point" 2>/dev/null || true
    rmdir "$mount_point" 2>/dev/null || true
}

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_gpt (GPT, 4 partitions)"
echo "=========================================="

IMG="/output/example_gpt/training_gpt.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    echo ""
    echo "  --- Partition table ---"
    mmls "$IMG" || true

    # Partition 1: FAT32
    echo ""
    echo "  --- Partition 1: FAT32 ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p1" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount FAT32 partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Partition 2: NTFS
    echo ""
    echo "  --- Partition 2: NTFS ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p2" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount NTFS partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Partition 3: exFAT
    echo ""
    echo "  --- Partition 3: exFAT ---"
    MNT=$(mktemp -d)
    if mount.exfat-fuse "/dev/mapper/${LOOPBASE}p3" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount exFAT partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Partition 4: ext3
    echo ""
    echo "  --- Partition 4: ext3 ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p4" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount ext3 partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_mbr (MBR, 4 partitions + extended)"
echo "=========================================="

IMG="/output/example_mbr/training_mbr.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    echo ""
    echo "  --- Partition table ---"
    mmls "$IMG" || true

    # Partition 1: FAT32
    echo ""
    echo "  --- Partition 1: FAT32 ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p1" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount FAT32 partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Partition 2: NTFS
    echo ""
    echo "  --- Partition 2: NTFS ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p2" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount NTFS partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Partition 3: exFAT
    echo ""
    echo "  --- Partition 3: exFAT ---"
    MNT=$(mktemp -d)
    if mount.exfat-fuse "/dev/mapper/${LOOPBASE}p3" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount exFAT partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Partition 5: ext3 (logical inside extended)
    echo ""
    echo "  --- Partition 5: ext3 (logical) ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p5" "$MNT" 2>/dev/null; then
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount ext3 logical partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_luks (GPT + LUKS encryption)"
echo "=========================================="

IMG="/output/example_luks/training_luks.img"
LUKS_PASS="secret123"

if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    echo ""
    echo "  --- Partition table ---"
    mmls "$IMG" || true

    PARTDEV="/dev/mapper/${LOOPBASE}p1"

    # Verify LUKS header is present
    echo ""
    echo "  --- LUKS detection ---"
    if cryptsetup isLuks "$PARTDEV" 2>/dev/null; then
        pass "LUKS header detected on partition 1"
    else
        fail "No LUKS header on partition 1"
    fi

    # Decrypt with passphrase
    echo ""
    echo "  --- LUKS decryption with passphrase ---"
    LUKS_NAME="verify_luks_test"
    if echo -n "$LUKS_PASS" | cryptsetup open "$PARTDEV" "$LUKS_NAME" 2>/dev/null; then
        pass "LUKS decrypted successfully with passphrase"

        MNT=$(mktemp -d)
        if mount "/dev/mapper/$LUKS_NAME" "$MNT" 2>/dev/null; then
            verify_files "$MNT"
            cleanup_mount "$MNT"
        else
            fail "Could not mount decrypted LUKS volume"
            rmdir "$MNT" 2>/dev/null || true
        fi

        cryptsetup close "$LUKS_NAME"
    else
        fail "LUKS decryption failed with passphrase '$LUKS_PASS'"
    fi

    # Verify wrong passphrase fails
    echo ""
    echo "  --- LUKS wrong passphrase rejection ---"
    if echo -n "wrongpassword" | cryptsetup open "$PARTDEV" "verify_luks_bad" 2>/dev/null; then
        fail "LUKS accepted wrong passphrase (should have rejected)"
        cryptsetup close "verify_luks_bad" 2>/dev/null || true
    else
        pass "LUKS correctly rejected wrong passphrase"
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_veracrypt (Full-disk VeraCrypt)"
echo "=========================================="

IMG="/output/example_veracrypt/training_veracrypt.img"
VC_PASS="secret123"

if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    # Ensure device-mapper is ready
    dmsetup mknodes 2>/dev/null || true

    # Decrypt and map with VeraCrypt
    echo ""
    echo "  --- VeraCrypt decryption with passphrase ---"
    MNT=$(mktemp -d)
    if veracrypt --text --mount "$IMG" "$MNT" \
        --password "$VC_PASS" --pim 0 --keyfiles "" \
        --non-interactive --mount-options=nokernelcrypto 2>/dev/null; then
        pass "VeraCrypt decrypted and mounted successfully"

        verify_files "$MNT"

        umount "$MNT" 2>/dev/null || true
        veracrypt --text --dismount "$IMG" 2>/dev/null || true
    else
        fail "VeraCrypt decryption failed with passphrase '$VC_PASS'"
    fi
    rmdir "$MNT" 2>/dev/null || true

    # Verify wrong passphrase fails
    echo ""
    echo "  --- VeraCrypt wrong passphrase rejection ---"
    MNT2=$(mktemp -d)
    if veracrypt --text --mount "$IMG" "$MNT2" \
        --password "wrongpassword" --pim 0 --keyfiles "" \
        --non-interactive --mount-options=nokernelcrypto 2>/dev/null; then
        fail "VeraCrypt accepted wrong passphrase (should have rejected)"
        umount "$MNT2" 2>/dev/null || true
        veracrypt --text --dismount "$IMG" 2>/dev/null || true
    else
        pass "VeraCrypt correctly rejected wrong passphrase"
    fi
    rmdir "$MNT2" 2>/dev/null || true
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_raw (RAW superfloppy)"
echo "=========================================="

IMG="/output/example_raw/training_raw.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")

    # RAW disks should NOT have a partition table
    echo ""
    echo "  --- No partition table (raw) ---"
    if mmls "$IMG" > /dev/null 2>&1; then
        fail "Partition table found on RAW disk (should have none)"
    else
        pass "No partition table detected (correct for RAW)"
    fi

    # Should have a filesystem directly on the device
    echo ""
    echo "  --- Direct filesystem ---"
    MNT=$(mktemp -d)
    if mount "$LOOP" "$MNT" 2>/dev/null; then
        pass "Mounted raw filesystem directly"
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount raw filesystem"
        rmdir "$MNT" 2>/dev/null || true
    fi

    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_template (OS template)"
echo "=========================================="

IMG="/output/example_template/training_template.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    echo ""
    echo "  --- Partition 1: NTFS with Windows 10 template ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p1" "$MNT" 2>/dev/null; then
        pass "Mounted NTFS partition"

        # Verify Windows 10 template directories
        for dir in "Windows/System32" "Windows/System32/config" "Windows/System32/winevt/Logs" \
                   "Windows/Prefetch" "Program Files" "Users/Default/Documents" \
                   "\$Recycle.Bin"; do
            if [ -d "$MNT/$dir" ]; then
                pass "Template dir: $dir"
            else
                fail "Missing template dir: $dir"
            fi
        done

        # Verify stub files
        for f in "Windows/System32/config/SAM" "Windows/System32/config/SYSTEM" \
                 "Users/Default/NTUSER.DAT" "Windows/bootmgr"; do
            if [ -f "$MNT/$f" ]; then
                pass "Template file: $f"
            else
                fail "Missing template file: $f"
            fi
        done

        # Verify scenario files were added into template structure
        if [ -f "$MNT/Users/Default/Documents/doc1.docx" ]; then
            pass "Scenario file placed in template dir"
        else
            fail "Scenario file missing from template dir"
        fi

        # Verify deleted file is gone
        if [ ! -f "$MNT/Users/Default/Documents/text1.txt" ]; then
            pass "text1.txt was deleted (not present)"
        else
            fail "text1.txt should have been deleted"
        fi

        cleanup_mount "$MNT"
    else
        fail "Could not mount NTFS partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_btrfs (btrfs + Linux template)"
echo "=========================================="

IMG="/output/example_btrfs/training_btrfs.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    echo ""
    echo "  --- Partition 1: btrfs ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p1" "$MNT" 2>/dev/null; then
        pass "Mounted btrfs partition"

        # Verify Linux template directories
        for dir in "etc" "var/log" "home" "usr/bin" "root"; do
            if [ -d "$MNT/$dir" ]; then
                pass "Template dir: $dir"
            else
                fail "Missing template dir: $dir"
            fi
        done

        # Verify Linux template stub files
        for f in "etc/passwd" "etc/shadow" "var/log/syslog"; do
            if [ -f "$MNT/$f" ]; then
                pass "Template file: $f"
            else
                fail "Missing template file: $f"
            fi
        done

        # Verify scenario files in /home
        check_file_on_mount "$MNT/home" "doc1.docx"
        check_file_absent "$MNT/home" "text1.txt"

        cleanup_mount "$MNT"
    else
        fail "Could not mount btrfs partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_f2fs (F2FS filesystem)"
echo "=========================================="

IMG="/output/example_f2fs/training_f2fs.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    echo ""
    echo "  --- Partition 1: F2FS ---"
    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p1" "$MNT" 2>/dev/null; then
        pass "Mounted F2FS partition"
        verify_files "$MNT"
        cleanup_mount "$MNT"
    else
        fail "Could not mount F2FS partition"
        rmdir "$MNT" 2>/dev/null || true
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_inject (unallocated space injection)"
echo "=========================================="

IMG="/output/example_inject/training_inject.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    # Verify hidden data is findable with strings
    echo ""
    echo "  --- Hidden data in unallocated space ---"
    if strings "$IMG" | grep -q "BitLocker Recovery Key"; then
        pass "Found BitLocker Recovery Key in raw image"
    else
        fail "BitLocker Recovery Key not found in raw image"
    fi

    if strings "$IMG" | grep -q "Tr4ining"; then
        pass "Found hidden password in raw image"
    else
        fail "Hidden password not found in raw image"
    fi

    # Verify hidden data is NOT visible in the mounted filesystem
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")

    MNT=$(mktemp -d)
    if mount "/dev/mapper/${LOOPBASE}p1" "$MNT" 2>/dev/null; then
        # Search all files on the filesystem for the hidden string
        if grep -r "BitLocker Recovery Key" "$MNT" 2>/dev/null; then
            fail "Hidden data visible in filesystem (should only be in unallocated space)"
        else
            pass "Hidden data NOT visible in filesystem (correct)"
        fi
        cleanup_mount "$MNT"
    else
        fail "Could not mount partition for inject verification"
        rmdir "$MNT" 2>/dev/null || true
    fi

    # Verify partition table shows unallocated gap
    if mmls "$IMG" 2>/dev/null | grep -q "Unallocated"; then
        pass "Unallocated space visible in partition table"
    else
        fail "No unallocated space shown in partition table"
    fi

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_mbr (boot code)"
echo "=========================================="

IMG="/output/example_mbr/training_mbr.img"
if [ -f "$IMG" ]; then
    echo ""
    echo "  --- MBR boot code ---"
    # Check for the boot message string in the first 446 bytes
    if dd if="$IMG" bs=446 count=1 2>/dev/null | grep -q "Non-system"; then
        pass "Boot code message found in MBR"
    else
        fail "Boot code message not found in MBR"
    fi

    # Check for 55 AA boot signature at bytes 510-511
    SIG=$(dd if="$IMG" bs=1 skip=510 count=2 2>/dev/null | od -A n -t x1 | tr -d ' ')
    if [ "$SIG" = "55aa" ]; then
        pass "MBR boot signature 55AA present"
    else
        fail "MBR boot signature missing (got: $SIG)"
    fi
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_countermeasures (hidden root entries)"
echo "=========================================="

# Hidden name still present in raw bytes. Searches the first 5 characters as
# UTF-16LE, which sit contiguously in both a FAT LFN slot and an exFAT name entry.
raw_has_name() {
    python3 -c 'import sys; sys.exit(0 if sys.argv[2][:5].encode("utf-16-le") in open(sys.argv[1],"rb").read() else 1)' "$1" "$2"
}

# Mount a partition, then check visible files are listed and hidden ones are not
check_hidden_on_mount() {
    local dev="$1" fs="$2" visible="$3" hidden="$4"
    local mnt
    mnt=$(mktemp -d)
    if [ "$fs" = "exfat" ]; then
        mount.exfat-fuse -o ro "$dev" "$mnt" 2>/dev/null
    else
        mount -o ro "$dev" "$mnt" 2>/dev/null
    fi || { fail "Could not mount $fs partition $dev"; rmdir "$mnt"; return; }
    for f in $visible; do check_file_on_mount "$mnt" "$f"; done
    for f in $hidden; do
        if [ ! -e "$mnt/$f" ] && ! ls -a "$mnt/$(dirname "$f")" | grep -qx "$(basename "$f")"; then
            pass "$f hidden from mounted filesystem"
        else
            fail "$f should be hidden but is visible"
        fi
    done
    cleanup_mount "$mnt"
    sleep 1  # let the FUSE driver release the device
}

# Names an END-terminated walk of a directory's $I30 index returns, the way
# Windows lists a directory. Reads the raw device with DiskForge's own parser.
ntfs_walk_has() {
    local dev="$1" path="$2"
    PYTHONPATH=/app python3 - "$dev" "$path" <<'PY'
import sys
from diskforge.countermeasures import _ntfs_volume, _ntfs_leaf, _ntfs_entries
dev, path = sys.argv[1], sys.argv[2].split("/")
with open(dev, "rb") as f:
    vol, mft = _ntfs_volume(f), 5
    for i, name in enumerate(path):
        buf, node, _ = _ntfs_leaf(f, vol, mft)
        match = [e for e in _ntfs_entries(buf, node) if e["name"] == name]
        if not match:
            sys.exit(3)  # not listed; any other failure exits 1
        mft = match[0]["ref"]
PY
}

# Patched ntfs-3g (Debian, CVE-2026-46572) refuses an index whose END entry does
# not end the in-use area, which is exactly what ntfs_index_flag leaves behind.
# The partition cannot be mounted on Linux, so check what a Windows-style walk sees.
check_flag_partition() {
    local dev="$1" visible="$2" hidden="$3"
    local mnt out
    mnt=$(mktemp -d)
    if out=$(ntfs-3g -o ro "$dev" "$mnt" 2>&1); then
        fail "ntfs-3g mounted a flagged index (expected the strict END check to refuse it)"
        umount "$mnt"
    elif echo "$out" | grep -q "Corrupt index entry stream"; then
        pass "ntfs-3g refuses the flagged index (Corrupt index entry stream)"
    else
        fail "ntfs-3g failed for another reason: $out"
    fi
    rmdir "$mnt"
    for f in $visible; do check "$f listed by an END-terminated index walk" ntfs_walk_has "$dev" "$f"; done
    for f in $hidden; do check "$f hidden from an END-terminated index walk" bash -c "ntfs_walk_has '$dev' '$f'; [ \$? -eq 3 ]"; done
}
export -f ntfs_walk_has

IMG="/output/example_countermeasures/training_countermeasures.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")
    P="/dev/mapper/${LOOPBASE}p"

    echo ""
    echo "  --- Partition 1: FAT32 fat_dir_zero ---"
    check_hidden_on_mount "${P}1" fat32 "text1.txt zip1.zip images/pic1.jpg" "doc1.docx copyofdocument1.docx"
    for f in doc1.docx copyofdocument1.docx; do
        check "$f name still in raw directory entries" raw_has_name "${P}1" "$f"
    done

    echo ""
    echo "  --- Partition 2: exFAT fat_dir_zero ---"
    check_hidden_on_mount "${P}2" exfat "copyofdocument1.docx text1.txt zip1.zip images/pic1.jpg" "doc1.docx"
    check "doc1.docx name still in raw directory entries" raw_has_name "${P}2" doc1.docx

    echo ""
    echo "  --- Partition 3: NTFS ntfs_index_flag ---"
    check_flag_partition "${P}3" "doc1.docx copyofdocument1.docx text1.txt images/pic1.jpg" "zip1.zip"
    check "TSK still lists zip1.zip" bash -c "fls '${P}3' | grep -q 'zip1.zip'"

    echo ""
    echo "  --- Partition 4: NTFS ntfs_index_truncate ---"
    check_hidden_on_mount "${P}4" ntfs "doc1.docx copyofdocument1.docx images/pic1.jpg" "text1.txt zip1.zip"
    for f in text1.txt zip1.zip; do
        check "TSK recovers $f from index slack (unallocated name)" bash -c "fls '${P}4' | grep -qE '^-/r .*$f$'"
    done
    check "ntfsfix accepts the truncated index (passes the strict END check)" ntfsfix -n "${P}4"

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# Same methods on a subdirectory (/images). The small NTFS directory keeps its
# index resident in the MFT record instead of an INDX block.
IMG="/output/example_countermeasures/training_countermeasures_subdir.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    LOOPBASE=$(basename "$LOOP")
    P="/dev/mapper/${LOOPBASE}p"
    # Each partition has two countermeasures: /images hides pic1.jpg, / hides one root entry
    SUB_VISIBLE="doc1.docx text1.txt images/doc1.docx images/copyofdocument1.docx"

    echo ""
    echo "  --- Subdirectory, partition 1: FAT32, hides /images itself and /images/pic1.jpg ---"
    check_hidden_on_mount "${P}1" fat32 "doc1.docx text1.txt zip1.zip" "images"
    check "pic1.jpg name still in raw directory entries" raw_has_name "${P}1" pic1.jpg
    check "images name still in raw directory entries" raw_has_name "${P}1" images

    echo ""
    echo "  --- Subdirectory, partition 2: exFAT fat_dir_zero ---"
    check_hidden_on_mount "${P}2" exfat "$SUB_VISIBLE" "images/pic1.jpg zip1.zip"
    check "pic1.jpg name still in raw directory entries" raw_has_name "${P}2" pic1.jpg

    echo ""
    echo "  --- Subdirectory, partition 3: NTFS ntfs_index_flag ---"
    check_flag_partition "${P}3" "$SUB_VISIBLE" "images/pic1.jpg zip1.zip"
    check "TSK still lists images/pic1.jpg" bash -c "fls '${P}3' \$(ifind -n images '${P}3') | grep -q 'pic1.jpg'"

    echo ""
    echo "  --- Subdirectory, partition 4: NTFS, truncate in /images and flag in / ---"
    check_flag_partition "${P}4" "$SUB_VISIBLE" "images/pic1.jpg zip1.zip"
    check "TSK recovers images/pic1.jpg from index slack (unallocated name)" bash -c "fls '${P}4' \$(ifind -n images '${P}4') | grep -qE '^-/r .*pic1.jpg$'"
    check "TSK still lists zip1.zip (flag method)" bash -c "fls '${P}4' | grep -qE '^r/r .*zip1.zip$'"

    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " VERIFYING: example_watermark (AI analysis notice)"
echo "=========================================="

CANARY="6f1c2a9e-4b7d-4e3a-9c58-2d0e8b71f4a3"

notice_count() {
    strings "$1" | grep -c "canary GUID $2" || true
}

IMG="/output/example_watermark/training_watermark.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    echo ""
    echo "  --- GPT disk, fixed canary, visible file on ---"
    check "Notice starts at sector 34 (gap after the GPT entry array)" bash -c "dd if='$IMG' bs=512 skip=34 count=1 2>/dev/null | grep -qa 'AI ANALYSIS NOTICE'"
    check "Notice names the owner" bash -c "strings '$IMG' | grep -q 'training material produced by JD Consultatory, LLC'"
    [ "$(notice_count "$IMG" "$CANARY")" -ge 4 ] && pass "Canary found in gap, tail, and both NOTICE.txt files" || fail "Expected the canary at least 4 times in the raw image"
    check "Backup GPT header still in the last sector" bash -c "[ \"\$(tail -c 512 '$IMG' | head -c 8)\" = 'EFI PART' ]"
    check "parted reads both partitions with no corruption warning" bash -c "out=\$(parted -s '$IMG' print 2>&1); echo \"\$out\" | grep -q ntfs && ! echo \"\$out\" | grep -qi corrupt"

    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    P="/dev/mapper/$(basename "$LOOP")p"
    for n in 1 2; do
        MNT=$(mktemp -d)
        if mount -o ro "${P}${n}" "$MNT" 2>/dev/null; then
            check "Partition $n has NOTICE.txt with the canary" grep -q "canary GUID $CANARY" "$MNT/NOTICE.txt"
            umount "$MNT"
        else
            fail "Could not mount partition $n"
        fi
        rmdir "$MNT"
    done
    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

IMG="/output/example_watermark/training_watermark_mbr.img"
if [ ! -f "$IMG" ]; then
    fail "Image not found: $IMG"
else
    echo ""
    echo "  --- MBR disk, auto canary, extended partition, inject at offset 0 ---"
    check "Notice in the gap after the MBR" bash -c "dd if='$IMG' bs=512 skip=34 count=1 2>/dev/null | grep -qa 'AI ANALYSIS NOTICE'"
    AUTO=$(strings "$IMG" | grep -o 'canary GUID [0-9a-f-]\{36\}' | sort -u)
    [ "$(echo "$AUTO" | wc -l)" -eq 1 ] && [ -n "$AUTO" ] && pass "One generated canary GUID ($AUTO)" || fail "Expected exactly one generated canary GUID, got: $AUTO"
    [ "$(notice_count "$IMG" "${AUTO#canary GUID }")" -eq 2 ] && pass "Canary in gap and tail only (file off)" || fail "Expected the canary exactly twice"
    check "Inject data at unallocated offset 0 survives" bash -c "strings '$IMG' | grep -q 'Tr4ining'"
    check "MBR signature intact" bash -c "[ \"\$(od -An -tx1 -j510 -N2 '$IMG' | tr -d ' \\n')\" = '55aa' ]"

    LOOP=$(losetup --find --show "$IMG")
    kpartx -a "$LOOP"
    P="/dev/mapper/$(basename "$LOOP")p"
    for n in 1 5; do
        check "ext4 partition $n passes fsck" e2fsck -fn "${P}${n}"
        MNT=$(mktemp -d)
        if mount -o ro "${P}${n}" "$MNT" 2>/dev/null; then
            [ ! -e "$MNT/NOTICE.txt" ] && pass "No NOTICE.txt on partition $n" || fail "NOTICE.txt present on partition $n with file off"
            umount "$MNT"
        else
            fail "Could not mount partition $n"
        fi
        rmdir "$MNT"
    done
    kpartx -d "$LOOP"
    losetup -d "$LOOP"
fi

# ============================================================
echo ""
echo "=========================================="
echo " RESULTS"
echo "=========================================="
echo "  Total:  $TESTS"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "=========================================="
echo ""

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
