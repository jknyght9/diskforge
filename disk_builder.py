import os
import sys
import json
import subprocess
from pathlib import Path

class DiskBuilder:
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.disks = []

    def run(self):
        self.load_manifest()
        self.validate_manifest()
        for disk in self.disks:
            self.create_disk_image(disk)
            self.partition_and_format_disk(disk)
            self.populate_disk(disk)

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
                        if not os.path.exists(file_entry["source"]):
                            self.fail(f"File does not exist: {file_entry['source']}")

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
            else:
                self.fail(f"Unsupported filesystem: {fs}")

    def partition_mbr(self, disk, loopdev):
        print("    Creating MBR partition table...")
        subprocess.run(["fdisk", loopdev], input=b"o\n", check=True)
        # You'd use `expect` or scripted input to `fdisk` here
        self.fail("MBR partition scripting not yet implemented")

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

        for part in disk["partitions"]:
            if "_dev" not in part:
                continue
            mount_point = mount_base / f"{disk['name']}_part{part['number']}"
            os.makedirs(mount_point, exist_ok=True)
            try:
                subprocess.run(["mount", part["_dev"], str(mount_point)], check=True)
                populate = part.get("populate", {})
                for file_entry in populate.get("add_files", []):
                    target_path = mount_point / file_entry["target"].lstrip("/")
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    subprocess.run(["cp", "-av", file_entry["source"], str(target_path)], check=True)
                for del_path in populate.get("delete_files", []):
                    full_path = mount_point / del_path.lstrip("/")
                    if full_path.exists():
                        full_path.unlink()
            finally:
                subprocess.run(["umount", str(mount_point)], check=True)
                os.rmdir(mount_point)

    def fail(self, msg):
        print(f"❌ {msg}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python disk_builder.py <manifest.json>")
        sys.exit(1)

    builder = DiskBuilder(sys.argv[1])
    builder.run()

