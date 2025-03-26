#!/bin/bash
set -e

mkdir -p /output
rm -f /output/*.img 
sleep 1

# Disk image filenames
MBR_DISK="mbr_disk_example.img"
GPT_DISK="gpt_disk_example.img"
DISK_SIZE=512M  # Adjust as needed

# Create empty disk images
truncate -s $DISK_SIZE $MBR_DISK
truncate -s $DISK_SIZE $GPT_DISK

# Create loopback devices
MBR_LOOP=$(losetup --find --show $MBR_DISK)
GPT_LOOP=$(losetup --find --show $GPT_DISK)


# ---------------------
# MBR PARTITIONING
# ---------------------
echo "Creating MBR partition table..."
(fdisk $MBR_LOOP <<EOF
o
n
p
1

+100M
t
c

n
p
2

+100M
t
2
7

n
p
3

+100M
t
3
7

n
p

+100M
t
4
83

w
EOF
) || > /dev/null # done because fdisk will throw an error and exit

echo "Refreshing MBR partition table..."
kpartx -a $MBR_LOOP  # Map partitions

#echo "Checking /dev/mapper/ for partition nodes..."
#ls -al /dev/mapper/loop*

echo "Formatting MBR partitions..."
mkfs.vfat -F32 -n "MBR_FAT32" /dev/mapper/$(basename ${MBR_LOOP})p1
mkfs.ntfs -f -L "MBR_NTFS" /dev/mapper/$(basename ${MBR_LOOP})p2
mkfs.exfat -n "MBR_EXFAT" /dev/mapper/$(basename ${MBR_LOOP})p3
mkfs.ext3 -L "MBR_EXT3" /dev/mapper/$(basename ${MBR_LOOP})p4

echo "MBR Partitioning and formatting complete!"

# ---------------------
# GPT PARTITIONING
# ---------------------
echo "Creating GPT partition table..."
parted -s $GPT_LOOP mklabel gpt
parted -s $GPT_LOOP mkpart primary fat32 1MiB 101MiB
parted -s $GPT_LOOP mkpart primary ntfs 101MiB 201MiB
parted -s $GPT_LOOP mkpart primary 201MiB 301MiB
parted -s $GPT_LOOP mkpart primary ext3 301MiB 401MiB

echo "Refreshing GPT partition table..."
kpartx -a $GPT_LOOP 
#ls -l /dev/mapper/loop*

echo "Formatting GPT partitions..."
mkfs.vfat -F32 -n "GPT_FAT32" /dev/mapper/$(basename ${GPT_LOOP})p1
mkfs.ntfs -f -L "GPT_NTFS" /dev/mapper/$(basename ${GPT_LOOP})p2
mkfs.exfat -n "GPT_EXFAT" /dev/mapper/$(basename ${GPT_LOOP})p3
mkfs.ext3 -L "GPT_EXT3" /dev/mapper/$(basename ${GPT_LOOP})p4

echo "GPT Partitioning and formatting complete!"

# ---------------------
# Cleanup
# ---------------------
losetup -d $MBR_LOOP
losetup -d $GPT_LOOP
kpartx -d $MBR_LOOP
kpartx -d $GPT_LOOP

mv /${MBR_DISK} /output/${MBR_DISK}
mv /${GPT_DISK} /output/${GPT_DISK}

echo "Disk images created successfully!"
