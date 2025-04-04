import glob
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

class DiskBuilder:
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.disks = []

    def run(self):
        output_dir = Path("/output")
        output_dir.mkdir(exist_ok=True)
        for img_file in output_dir.glob("*.img"):
            print(f"[~] Removing old image: {img_file}")
            img_file.unlink()

        self.load_manifest()
        self.validate_manifest()
        for disk in self.disks:
            self.create_disk_image(disk)
            self.partition_and_format_disk(disk)

        for disk in self.disks:
            self.populate_disk(disk)

            # cleanup and move image
            loopdev = disk.get("_loopdev")
            if loopdev:
                subprocess.run(["kpartx", "-d", loopdev], check=True)
                subprocess.run(["losetup", "-d", loopdev], check=True)

            final_path = f"/output/{os.path.basename(disk['_path'])}"
            shutil.move(disk["_path"], final_path)
            print(f"[+] Moved disk image to: {final_path}")

    def load_manifest(self):
        if not os.path.exists(self.manifest_path):
            self.fail(f"Manifest file not found: {self.manifest_path}")
        with open(self.manifest_path, 'r') as f:
            manifest = json.load(f)
            if 'disks' not in manifest:
                self.fail("Manifest must contain a 'disks' array")
            self.disks = manifest['disks']

    def validate_manifest(self):
        for disk in self.disks:
            for field in ["name", "type", "size", "partitions"]:
                if field not in disk:
                    self.fail(f"Missing required disk field '{field}'")
            if disk["type"] not in ["MBR", "GPT"]:
                self.fail(f"Invalid disk type '{disk['type']}'")
            for part in disk["partitions"]:
                for field in ["number", "type", "filesystem", "size"]:
                    if field not in part:
                        self.fail(f"Missing required partition field '{field}' in disk '{disk['name']}' partition number '{part['number']}'")
                if "populate" in part:
                    for file_entry in part["populate"].get("add_files", []):
                        matched_files = glob.glob(file_entry["source"])
                        if not matched_files:
                            self.fail(f"No matching files for pattern: {file_entry['source']}")

    def create_disk_image(self, disk):
        disk_path = f"output/{disk['name']}.img"
        print(f"[*] Creating disk image: {disk_path}")
        os.makedirs("output", exist_ok=True)
        subprocess.run(["truncate", "-s", disk["size"], disk_path], check=True)
        disk["_path"] = disk_path

    def partition_and_format_disk(self, disk):
        print(f"[*] Partitioning disk: {disk['name']}")
        disk_path = disk["_path"]
        loopdev = subprocess.check_output(["losetup", "--find", "--show", disk_path]).decode().strip()
        disk["_loopdev"] = loopdev

        if disk['type'] == "MBR":
            self.partition_mbr(disk, loopdev)
        elif disk['type'] == "GPT":
            self.partition_gpt(disk, loopdev)

        subprocess.run(["kpartx", "-a", loopdev], check=True)

        for part in disk["partitions"]:
            partnum = part["number"]
            partdev = f"/dev/mapper/{os.path.basename(loopdev)}p{partnum}"
            part["_dev"] = partdev
            label = part.get("label", f"{disk['name']}_part{partnum}")
            fs = part["filesystem"]
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
            elif fs in ("", "none", "null") or part["type"] == "extended":
                continue
            else:
                self.fail(f"Unsupported filesystem: {fs}")

    def partition_mbr(self, disk, loopdev):
        print("    Creating MBR partition table with sfdisk...")
        SECTORS_PER_MIB = 2048
        sfdisk_lines = ["label: dos"]
        start_sector = 2048
        total_sectors = int(disk['size'].replace('M', '')) * SECTORS_PER_MIB
        logical_parts = []
        extended_entry = None

        for part in disk["partitions"]:
            if part["type"] == "primary":
                part_type = self.get_mbr_type_code(part["filesystem"])
                size_mib = int(part["size"].replace("M", ""))
                size_sectors = size_mib * SECTORS_PER_MIB
                if start_sector + size_sectors > total_sectors:
                    self.fail(f"Partition {part['number']} (start {start_sector}, size {size_sectors}) exceeds disk bounds ({total_sectors} sectors)")
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
                    logical_type = self.get_mbr_type_code(logical["filesystem"])
                    size_mib = int(logical["size"].replace("M", ""))
                    size_sectors = size_mib * SECTORS_PER_MIB
                    if logical_start + size_sectors > total_sectors:
                        self.fail(f"Logical partition {logical['number']} (start {logical_start}, size {size_sectors}) exceeds disk bounds ({total_sectors} sectors)")
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

    def get_mbr_type_code(self, fs):
        return {
            "fat32": "c",
            "ntfs": "7",
            "ext2": "83",
            "ext3": "83",
            "ext4": "83",
            "xfs": "83",
            "exfat": "7"
        }.get(fs.lower(), "83")

    def partition_gpt(self, disk, loopdev):
        print("    Creating GPT partition table...")
        subprocess.run(["parted", "-s", loopdev, "mklabel", "gpt"], check=True)
        for part in disk["partitions"]:
            start = f"{1 + 100 * (part['number'] - 1)}MiB"
            end = f"{100 * part['number']}MiB"
            subprocess.run(["parted", "-s", loopdev, "mkpart", "primary", start, end], check=True)

    def populate_disk(self, disk):
        print(f"[*] Populating disk: {disk['name']}")
        mount_base = Path("/mnt/diskbuilder")
        os.makedirs(mount_base, exist_ok=True)

        def process_partition(part):
            if "_dev" not in part:
                return
            fs = part.get("filesystem", "").lower()
            if fs in ("", "none", "null"):
                return
            partnum = part["number"]
            mount_point = mount_base / f"{disk['name']}_part{partnum}"
            os.makedirs(mount_point, exist_ok=True)

            try:
                subprocess.run(["mount", part["_dev"], str(mount_point)], check=True)
                populate = part.get("populate", {})
                for file_entry in populate.get("add_files", []):
                    target_path = mount_point / file_entry["target"].lstrip("/")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    #subprocess.run(["cp", "-av", file_entry["source"], str(target_path)], check=True)

                    sources = glob.glob(file_entry["source"])
                    if not sources:
                        self.fail(f"No files matched pattern: {file_entry['source']}")

                    for src in sources:
                        if os.path.isdir(src):
                            subprocess.run(["cp", "-aRv", src, str(target_path)], check=True)
                        else:
                            subprocess.run(["cp", "-av", src, str(target_path)], check=True)

                # Flush all file data to disk
                subprocess.run(["sync"], check=True)

                for del_path in populate.get("delete_files", []):
                    full_path = mount_point / del_path.lstrip("/")
                    if full_path.exists():
                        full_path.unlink()
            finally:
                subprocess.run(["umount", str(mount_point)], check=True)
                os.rmdir(mount_point)

        for part in disk["partitions"]:
            if part["type"] == "extended":
                for logical in part.get("partitions", []):
                    process_partition(logical)
            else:
                process_partition(part)

    def fail(self, msg):
        print(f"❌ {msg}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python disk_builder.py <manifest.json>")
        sys.exit(1)

    builder = DiskBuilder(sys.argv[1])
    builder.run()

