import os, subprocess, sys, time
from pathlib import Path
from .utils import fail, wait_for_device
from .partitioning import partition_and_format_disk
from .populator import populate_disk

class DiskImage:
    def __init__(self, disk):
        self.disk = disk
        self.path = f"/output/{disk['name']}.img"
        self.loopdev = None

    def create(self):
        print(f"[*] Creating disk image: {self.path}", file=sys.stdout, flush=True)
        output_dir = os.path.dirname(self.path)

        for _ in range(5):
            if os.access(output_dir, os.W_OK):
                break
            print(f"[!] Waiting for output mount to be ready...")
            time.sleep(1)
        else:
            raise RuntimeError(f"Output directory not found {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        try:
            subprocess.run(["truncate", "-s", self.disk["size"], self.path], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create disk image: {e}")

        # Force the file to be visible and synced
        with open(self.path, 'ab') as f:
            os.fsync(f.fileno())

        subprocess.run(["sync"], check=True)
        self.disk["_path"] = self.path

    def partition(self):
        print(f"[*] Partitioning disk: {self.disk['name']}", file=sys.stdout, flush=True)
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Image not found at: {self.path}")

        # Attach the image as a loop device
        self.loopdev = subprocess.check_output(
            ["losetup", "--find", "--show", self.path]
        ).decode().strip()
        self.disk["_loopdev"] = self.loopdev

        # Check for VeraCrypt full-disk encryption (defined at disk level)
        disk_encrypt = self.disk.get("encrypt", {})
        if disk_encrypt.get("type") == "veracrypt":
            self._setup_veracrypt_full_disk(disk_encrypt)
            return

        # Normal partitioning flow
        partition_and_format_disk(self.disk)

    def _setup_veracrypt_full_disk(self, encrypt_cfg):
        """Handle VeraCrypt full-disk encryption as a distinct path."""
        loopdev = self.disk["_loopdev"]
        disk_path = self.disk["_path"]
        passphrase = encrypt_cfg["passphrase"]
        part = self.disk["partitions"][0]
        fs = part.get("filesystem", "ext4").lower()
        mount_path = f"/mnt/veracrypt_{self.disk['name']}"
        os.makedirs(mount_path, exist_ok=True)

        # Detach loop device — VeraCrypt works directly on the file
        subprocess.run(["losetup", "-d", loopdev], check=False)
        self.loopdev = None
        self.disk["_loopdev"] = None

        # Get the file size in bytes for VeraCrypt's --size flag
        file_size = os.path.getsize(disk_path)

        # Ensure device-mapper is available (required in Docker containers)
        os.makedirs("/dev/mapper", exist_ok=True)
        if not os.path.exists("/dev/mapper/control"):
            subprocess.run(["dmsetup", "mknodes"], check=False)

        print(f"[*] Creating VeraCrypt full-disk volume on {disk_path}")

        # Create encrypted volume without a filesystem (we format after mount)
        subprocess.run([
            "veracrypt", "--text", "--create", disk_path,
            "--volume-type", "normal",
            "--size", str(file_size),
            "--encryption", "AES",
            "--hash", "SHA-512",
            "--filesystem", "none",
            "--password", passphrase,
            "--pim", "0",
            "--keyfiles", "",
            "--non-interactive",
            "--quick"
        ], check=True)

        # Map the VeraCrypt volume without mounting (no filesystem yet)
        print(f"[*] Mapping VeraCrypt volume")
        subprocess.run([
            "veracrypt", "--text", "--mount", disk_path,
            "--password", passphrase,
            "--pim", "0",
            "--keyfiles", "",
            "--non-interactive",
            "--filesystem=none",
            "--mount-options=nokernelcrypto"
        ], check=True)

        # Find the mapped device from veracrypt --list
        # Output format: "1: /path/to/file /dev/loopN -" or "1: /path/to/file /dev/mapper/veracryptN /mount"
        vc_list = subprocess.check_output(
            ["veracrypt", "--text", "--list"]
        ).decode().strip()
        mapped_dev = None
        for line in vc_list.splitlines():
            if disk_path in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("/dev/"):
                        mapped_dev = p
                        break
                break

        if not mapped_dev:
            raise RuntimeError(f"Could not find VeraCrypt mapped device for {disk_path}")

        wait_for_device(mapped_dev)

        print(f"[*] VeraCrypt mapped to {mapped_dev}")

        # Format the filesystem on the mapped device
        label = part.get("label", f"{self.disk['name']}_vc")
        print(f"[*] Formatting VeraCrypt volume as {fs}")
        if fs == "fat32":
            subprocess.run(["mkfs.vfat", "-F32", "-n", label, mapped_dev], check=True)
        elif fs == "ntfs":
            subprocess.run(["mkfs.ntfs", "-f", "-L", label, mapped_dev], check=True)
        elif fs in ("ext2", "ext3", "ext4"):
            subprocess.run([f"mkfs.{fs}", "-L", label, mapped_dev], check=True)
        elif fs == "xfs":
            subprocess.run(["mkfs.xfs", "-L", label, mapped_dev], check=True)
        else:
            fail(f"Unsupported filesystem for VeraCrypt: {fs}")

        # Mount the formatted filesystem
        print(f"[*] Mounting VeraCrypt volume at {mount_path}")
        subprocess.run(["mount", mapped_dev, mount_path], check=True)

        # Mark the partition so the populator knows it's already mounted
        part["_dev"] = mount_path
        part["_veracrypt_mounted"] = True
        part["_veracrypt_mount_path"] = mount_path
        part["_veracrypt_disk_path"] = disk_path
        part["_already_mounted"] = True

    def populate(self):
        populate_disk(self.disk)

    def cleanup(self):
        print(f"[*] Cleaning up: {self.disk['name']}", file=sys.stdout, flush=True)

        # Dismount any VeraCrypt volumes
        for part in self.disk.get("partitions", []):
            if part.get("_veracrypt_mounted"):
                mount_path = part.get("_veracrypt_mount_path", "")
                disk_path = part.get("_veracrypt_disk_path", "")
                if mount_path:
                    subprocess.run(["umount", mount_path], check=False)
                # Dismount by the source file/device path
                target = disk_path or mount_path
                if target:
                    print(f"    Dismounting VeraCrypt: {target}")
                    subprocess.run(
                        ["veracrypt", "--text", "--dismount", target],
                        check=False
                    )

        # Remove kpartx mappings and detach loop device
        if self.loopdev:
            subprocess.run(["kpartx", "-d", self.loopdev], check=False)
            subprocess.run(["losetup", "-d", self.loopdev], check=False)

        print(f"[+] Disk image ready: {self.path}")
