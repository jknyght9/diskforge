import os, subprocess, sys
from diskforge.utils import fail, wait_for_device

def partition_and_format_disk(disk):
    print(f"[*] Partitioning disk: {disk['name']}", file=sys.stdout, flush=True)
    loopdev = disk["_loopdev"]

    if disk['type'] == "MBR":
        partition_mbr(disk, loopdev)
        if disk.get("bootable"):
            write_boot_code(disk, loopdev)
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
        luks_version = encrypt_cfg.get("version", "1")
        if luks_version not in ["1", "2"]:
            fail(f"Invalid LUKS version '{luks_version}' in disk '{disk['name']}' partition {partnum}. Supported: 1, 2")

        luks_name = f"luks_{disk['name']}_part{partnum}"
        mapped_path = f"/dev/mapper/{luks_name}"

        print(f"    Encrypting partition {partnum} with LUKS (version {luks_version})")

        subprocess.run(
            ["cryptsetup", "luksFormat", partdev, "-q", "--type", f"luks{luks_version}"],
            input=passphrase, check=True
        )

        subprocess.run(["cryptsetup", "open", partdev, luks_name], input=passphrase, check=True)
        wait_for_device(mapped_path)

        part["_dev"] = mapped_path
        part["_luks_name"] = luks_name
        part["_luks_open"] = True

    # Format the filesystem on the (possibly LUKS-mapped) device
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
    elif fs in ("hfsplus", "hfs+"):
        subprocess.run(["mkfs.hfsplus", "-v", label, dev_to_format], check=True)
    else:
        fail(f"Unsupported filesystem: {fs}")

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
        "exfat": "7",
        "hfsplus": "af",
        "hfs+": "af"
    }.get(fs.lower(), "83")

def write_boot_code(disk, loopdev):
    """Write boot code to the first 446 bytes of an MBR disk."""
    boot_code_path = disk.get("boot_code")
    if boot_code_path:
        if not os.path.exists(boot_code_path):
            fail(f"Boot code file not found: {boot_code_path}")
        with open(boot_code_path, "rb") as f:
            code = f.read(446)
        print(f"    Writing custom boot code from {boot_code_path}")
    else:
        code = _default_mbr_boot_code()
        print(f"    Writing default MBR boot code")

    # Pad to exactly 446 bytes, write to device (preserves partition table at 446-511)
    code = code[:446].ljust(446, b'\x00')
    with open(loopdev, "r+b") as dev:
        dev.write(code)

def _default_mbr_boot_code():
    """Generate a minimal x86 real-mode MBR boot stub.

    This 16-bit code runs at 0x7C00 in real mode:
      - Prints "Non-system disk or disk error"
      - Prints "Press any key to restart..."
      - Waits for a keypress
      - Reboots via INT 19h
    """
    # x86 real-mode assembly (NASM syntax for reference):
    #   ORG 0x7C00
    #   xor ax, ax
    #   mov ds, ax
    #   mov si, msg1
    #   call print
    #   mov si, msg2
    #   call print
    #   xor ah, ah       ; INT 16h AH=0: wait for key
    #   int 0x16
    #   int 0x19         ; reboot
    # print:
    #   lodsb
    #   or al, al
    #   jz .done
    #   mov ah, 0x0E
    #   int 0x10
    #   jmp print
    # .done:
    #   ret
    # msg1: db "Non-system disk or disk error", 0x0D, 0x0A, 0
    # msg2: db "Press any key to restart...", 0x0D, 0x0A, 0
    msg1 = b"Non-system disk or disk error\r\n\x00"
    msg2 = b"Press any key to restart...\r\n\x00"

    # Hand-assembled x86 machine code
    code = bytearray()
    # xor ax, ax
    code += b'\x31\xc0'
    # mov ds, ax
    code += b'\x8e\xd8'
    # mov si, offset msg1 (will patch after)
    code += b'\xbe'
    msg1_offset_pos = len(code)
    code += b'\x00\x00'  # placeholder
    # call print
    code += b'\xe8'
    print_call1_pos = len(code)
    code += b'\x00\x00'  # placeholder
    # mov si, offset msg2 (will patch after)
    code += b'\xbe'
    msg2_offset_pos = len(code)
    code += b'\x00\x00'  # placeholder
    # call print
    code += b'\xe8'
    print_call2_pos = len(code)
    code += b'\x00\x00'  # placeholder
    # xor ah, ah
    code += b'\x30\xe4'
    # int 0x16 (wait for keypress)
    code += b'\xcd\x16'
    # int 0x19 (reboot)
    code += b'\xcd\x19'

    # print subroutine
    print_offset = len(code)
    # lodsb
    code += b'\xac'
    # or al, al
    code += b'\x08\xc0'
    # jz .done (2 bytes forward: jz +5)
    code += b'\x74\x04'
    # mov ah, 0x0E
    code += b'\xb4\x0e'
    # int 0x10
    code += b'\xcd\x10'
    # jmp print (-8 from here)
    code += b'\xeb\xf6'
    # ret
    code += b'\xc3'

    # Messages
    msg1_abs = 0x7C00 + len(code)
    code += msg1
    msg2_abs = 0x7C00 + len(code)
    code += msg2

    # Patch offsets (all relative to 0x7C00)
    code[msg1_offset_pos] = msg1_abs & 0xFF
    code[msg1_offset_pos + 1] = (msg1_abs >> 8) & 0xFF

    code[msg2_offset_pos] = msg2_abs & 0xFF
    code[msg2_offset_pos + 1] = (msg2_abs >> 8) & 0xFF

    # Patch call offsets (relative: target - (call_addr + 2))
    call1_addr = 0x7C00 + print_call1_pos
    rel1 = (0x7C00 + print_offset) - (call1_addr + 2)
    code[print_call1_pos] = rel1 & 0xFF
    code[print_call1_pos + 1] = (rel1 >> 8) & 0xFF

    call2_addr = 0x7C00 + print_call2_pos
    rel2 = (0x7C00 + print_offset) - (call2_addr + 2)
    code[print_call2_pos] = rel2 & 0xFF
    code[print_call2_pos + 1] = (rel2 >> 8) & 0xFF

    return bytes(code)

def partition_gpt(disk, loopdev):
    print("    Creating GPT partition table...")
    subprocess.run(["parted", "-s", loopdev, "mklabel", "gpt"], check=True)

    start_mib = 1  # Leave 1MiB for GPT header

    for part in disk["partitions"]:
        size_mib = int(part["size"].replace("M", ""))
        end_mib = start_mib + size_mib
        subprocess.run([
            "parted", "-s", loopdev, "mkpart", "primary",
            f"{start_mib}MiB", f"{end_mib}MiB"
        ], check=True)
        start_mib = end_mib
