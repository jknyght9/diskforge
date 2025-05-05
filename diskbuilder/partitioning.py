import os, subprocess, sys
from diskbuilder.utils import fail,wait_for_device

def partition_and_format_disk(disk):
    print(f"[*] Partitioning disk: {disk['name']}", file=sys.stdout, flush=True)
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
    wait_for_device(partdev)

    part["_dev"] = partdev
    label = part.get("label", f"{disk['name']}_part{partnum}")
    fs = part.get("filesystem", "").lower()
    encrypt_cfg = part.get("encrypt", {})

    if fs in ("", "none", "null"):
        print(f"    Skipping formatting of partition {partnum} (no filesystem)")
        return

    # LUKS encryption
    if encrypt_cfg.get("type") == "luks":
        passphrase = encrypt_cfg.get("passphrase", "").encode()
        luks_name = f"luks_{disk['name']}_part{partnum}"
        mapped_path = f"/dev/mapper/{luks_name}"

        print(f"    Encrypting partition {partnum} with LUKS...")
        subprocess.run(["cryptsetup", "luksFormat", partdev, "-q"], input=passphrase, check=True)
        subprocess.run(["cryptsetup", "open", partdev, luks_name], input=passphrase, check=True)
        wait_for_device(mapped_path)

        part["_dev"] = mapped_path
        part["_luks_name"] = luks_name  # Store name for later closure
        part["_luks_open"] = True

    # VERACRYPT encryption
    elif encrypt_cfg.get("type") == "veracrypt":
        passphrase = encrypt_cfg.get("passphrase", "")
        loopdev = disk["_loopdev"]
        mount_path = f"/mnt/veracrypt_{disk['name']}"
        os.makedirs(mount_path, exist_ok=True)

        print(f"    Encrypting full disk with VeraCrypt on {loopdev}")

            # Ensure device is free
        subprocess.run(["losetup", "-d", loopdev], check=False)
        subprocess.run(["losetup", "--find", "--show", disk["_path"]], check=True)  # re-attach cleanly
        loopdev = subprocess.check_output(["losetup", "--find", "--show", disk["_path"]]).decode().strip()
        disk["_loopdev"] = loopdev

        # Create encrypted volume
        subprocess.run([
            "veracrypt", "--text", "--create", loopdev,
            "--volume-type", "normal",
            "--encryption", "AES", 
            "--hash", "SHA-512",
            "--filesystem", fs,
            "--password", passphrase,
            "--pim", "0", 
            "--keyfiles", "",
            "--non-interactive",
            "--quick"
        ], check=True)

        # Mount VeraCrypt volume to container path
        subprocess.run([
            "veracrypt", "--text", "--mount", loopdev, mount_path,
            "--password", passphrase, 
            "--pim", "0", 
            "--keyfiles", "",
            "--non-interactive",
            "--mount-options=system"
        ], check=True)
        wait_for_device(mount_path)

        part["_dev"] = mount_path
        part["_veracrypt_mounted"] = True
        part["_veracrypt_mount_path"] = mount_path
        return

    # Final device to format
    dev_to_format = part["_dev"]

    print(f"    Formatting partition {partnum} as {fs}")
    if fs == "fat32":
        subprocess.run(["mkfs.vfat", "-F32", "-n", label, dev_to_format], check=True)
    elif fs == "ntfs":
        subprocess.run(["mkfs.ntfs", "-f", "-L", label, dev_to_format], check=True)
    elif fs == "ext2":
        subprocess.run(["mkfs.ext2", "-L", label, dev_to_format], check=True)
    elif fs == "ext3":
        subprocess.run(["mkfs.ext3", "-L", label, dev_to_format], check=True)
    elif fs == "ext4":
        subprocess.run(["mkfs.ext4", "-L", label, dev_to_format], check=True)
    elif fs == "xfs":
        subprocess.run(["mkfs.xfs", "-L", label, dev_to_format], check=True)
    elif fs == "exfat":
        subprocess.run(["mkfs.exfat", "-n", label, dev_to_format], check=True)
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
