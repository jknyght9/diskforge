#!/bin/bash
set -e

FILES_DIR="/files"
OUTPUT_DIR="/output"
WORK_DIR="/mnt/disk_mounts"
mkdir -p $WORK_DIR

function mount_and_populate {
    local disk_img=$1
    local label_prefix=$2

    echo "[*] Working on $disk_img"

    # Setup loop device
    LOOP_DEV=$(losetup --find --show "$OUTPUT_DIR/$disk_img")
    echo "    Loop device: $LOOP_DEV"

    # Create mappings for partitions
    kpartx -av $LOOP_DEV
    sleep 1  # let device settle

    for i in {1..4}; do
        PART_DEV="/dev/mapper/$(basename $LOOP_DEV)p$i"
        MOUNT_POINT="$WORK_DIR/${label_prefix}_part$i"
        mkdir -p "$MOUNT_POINT"

        echo "    Mounting $PART_DEV at $MOUNT_POINT"
        if blkid "$PART_DEV" | grep -qi exfat; then
            echo "    Using FUSE to mount exFAT: $PART_DEV"
            mount.exfat-fuse "$PART_DEV" "$MOUNT_POINT"
        else 
          mount "$PART_DEV" "$MOUNT_POINT"
        fi

        echo "    Copying files to $MOUNT_POINT"
        cp -av "$FILES_DIR"/* "$MOUNT_POINT"

        echo "    Deleting doc1.docx to simulate deletion"
        rm -f "$MOUNT_POINT/doc1.docx"

        echo "    Syncing and unmounting $MOUNT_POINT"
        sync
        umount "$MOUNT_POINT"
        rmdir "$MOUNT_POINT"
    done

    echo "    Cleaning up kpartx and loop device"
    kpartx -d $LOOP_DEV
    losetup -d $LOOP_DEV
}

mount_and_populate "mbr_disk_example.img" "MBR"
mount_and_populate "gpt_disk_example.img" "GPT"

echo "[✓] Disk images populated and cleaned up!"
