import os
import subprocess
from diskbuilder.utils import fail

def partition_and_format_disk(disk):
    print(f"[*] Partitioning disk: {disk['name']}")
    disk_path = disk["_path"]
    loopdev = disk["_loopdev"]

    if disk['type'] == "MBR":
        partition_mbr(disk, loopdev)
    elif disk['type'] == "GPT":
        partition_gpt(disk, loopdev)

    subprocess.run(["kpartx", "-a", loopdev], check=True)

    for part in disk["partitions"]:
        assign_and_format(part, disk, loopdev)

def assign_and_format(part, disk, loopdev):
    if part["type"] == "extended":
        for logical in part.get("partitions", []):
            assign_and_format(logical, disk, loopdev)
        return

    partnum = part["number"]
    partdev = f"/dev/mapper/{os.path.basename(loopdev)}p{partnum}"
    part["_dev"] = partdev
    label = part.get("label", f"{disk['name']}_part{partnum}")
    fs = part.get("filesystem", "").lower()

    if fs in ("", "none", "null"):
        print(f"    Skipping formatting of partition {partnum} (no filesystem)")
        return

    print(f"    Formatting partition {partnum} as {fs}")
    if fs == "fat32":
        subprocess.run(["mkfs.vfat", "-F32", "-n", label, partdev], check=True)
    elif fs == "ntfs":
        subprocess.run(["mkfs.ntfs", "-f", "-L", label, partdev], check=True)
    elif fs == "ext2":
        subprocess.run(["mkfs.ext2", "-L", label, partdev], check=True)
    elif fs == "ext3":
        subprocess.run(["mkfs.ext3", "-L", label, partdev], check=True)
    elif fs == "ext4":
        subprocess.run(["mkfs.ext4", "-L", label, partdev], check=True)
    elif fs == "xfs":
        subprocess.run(["mkfs.xfs", "-L", label, partdev], check=True)
    elif fs == "exfat":
        subprocess.run(["mkfs.exfat", "-n", label, partdev], check=True)
    else:
        self.fail(f"Unsupported filesystem: {fs}")

def partition_mbr(disk, loopdev):
    print("    Creating MBR partition table with sfdisk...")
    SECTORS_PER_MIB = 2048
    sfdisk_lines = ["label: dos"]
    start_sector = 2048
    total_sectors = int(disk['size'].replace('M', '')) * SECTORS_PER_MIB
    logical_parts = []
    extended_entry = None

    for part in disk["partitions"]:
        if part["type"] == "primary":
            part_type = get_mbr_type_code(part["filesystem"])
            size_mib = int(part["size"].replace("M", ""))
            size_sectors = size_mib * SECTORS_PER_MIB
            if start_sector + size_sectors > total_sectors:
                fail(f"Partition {part['number']} (start {start_sector}, size {size_sectors}) exceeds disk bounds ({total_sectors} sectors)")
            sfdisk_lines.append(
                f"{loopdev}p{part['number']} : start={start_sector}, size={size_sectors}, type={part_type}"
            )
            start_sector += size_sectors

        elif part["type"] == "extended":
            extended_start = start_sector
            logical_start = extended_start + SECTORS_PER_MIB
            extended_size_sectors = 0
            extended_entry = (part["number"], extended_start)

            for logical in part.get("partitions", []):
                logical_type = get_mbr_type_code(logical["filesystem"])
                size_mib = int(logical["size"].replace("M", ""))
                size_sectors = size_mib * SECTORS_PER_MIB
                if logical_start + size_sectors > total_sectors:
                    fail(f"Logical partition {logical['number']} (start {logical_start}, size {size_sectors}) exceeds disk bounds ({total_sectors} sectors)")
                logical_parts.append(
                    (f"{loopdev}p{logical['number']} : start={logical_start}, size={size_sectors}, type={logical_type}", logical_start)
                )
                logical_start += size_sectors
                extended_size_sectors = logical_start - extended_start

            if extended_entry:
                sfdisk_lines.append(
                    f"{loopdev}p{extended_entry[0]} : start={extended_entry[1]}, size={extended_size_sectors}, type=5"
                )

    for line, _ in sorted(logical_parts, key=lambda x: x[1]):
        sfdisk_lines.append(line)

    def extract_start(line):
        if line.startswith("label"):
            return -1
        for part in line.split():
            if part.startswith("start="):
                return int(part.split("=")[1].rstrip(","))
        return float("inf")

    sfdisk_sorted = sorted(sfdisk_lines, key=extract_start)
    sfdisk_str = "\n".join(sfdisk_sorted).encode()
    subprocess.run(["sfdisk", loopdev], input=sfdisk_str, check=True)

def get_mbr_type_code(fs):
    return {
        "fat32": "c",
        "ntfs": "7",
        "ext2": "83",
        "ext3": "83",
        "ext4": "83",
        "xfs": "83",
        "exfat": "7"
    }.get(fs.lower(), "83")

def partition_gpt(disk, loopdev):
    print("    Creating GPT partition table...")
    subprocess.run(["parted", "-s", loopdev, "mklabel", "gpt"], check=True)
    for part in disk["partitions"]:
        start = f"{1 + 100 * (part['number'] - 1)}MiB"
        end = f"{100 * part['number']}MiB"
        subprocess.run(["parted", "-s", loopdev, "mkpart", "primary", start, end], check=True)
