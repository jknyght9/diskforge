import os, subprocess, shutil, glob, sys, time
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
            if not os.path.exists(output_dir):
                raise RuntimeError(f"Output directory still missing: {output_dir}")
            if not os.access(output_dir, os.W_OK):
                raise RuntimeError(f"Output directory not writable: {output_dir}")
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

        # Ensure stale devices are removed before reuse
        subprocess.run(["losetup", "-D"], check=False)
        subprocess.run(["kpartx", "-d", "/dev/loop*"], check=False)
        subprocess.run(["dmsetup", "remove_all"], check=False)  

        # Attach the image as a loop device
        self.loopdev = subprocess.check_output(["losetup", "--find", "--show", self.path]).decode().strip()
        self.disk["_loopdev"] = self.loopdev

        # Detect full disk VeraCrypt encryption (no partitions, but encryption defined at disk level)
        is_veracrypt_full_disk = (
            not self.disk.get("partitions") and
            self.disk.get("encrypt", {}).get("type") == "veracrypt"
        )

        if is_veracrypt_full_disk:
            print(f"[*] Skipping partitioning for VeraCrypt full disk encryption", file=sys.stdout, flush=True)
            partition_and_format_disk(self.disk)  # triggers VeraCrypt encryption
            return

        partition_and_format_disk(self.disk)
        subprocess.run(["kpartx", "-a", self.loopdev], check=True)

    def populate(self):
        populate_disk(self.disk)

    def cleanup(self):
        print(f"[*] Cleaning up loop devices for {self.disk['name']}", file=sys.stdout, flush=True)
        if self.loopdev:
            try:
                subprocess.run(["kpartx", "-d", self.loopdev], check=True)
                subprocess.run(["losetup", "-d", self.loopdev], check=True)
            except subprocess.CalledProcessError as e:
                print(f"[!] Warning: Cleanup failed: {e}")
        final_path = f"/output/{os.path.basename(self.path)}"
        if os.path.exists(self.path):
            shutil.move(self.path, final_path)
            print(f"[+] Moved disk image to: {final_path}")
