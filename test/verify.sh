#!/bin/bash
# Verification script for diskbuilder images
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
