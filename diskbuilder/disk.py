import os, subprocess, shutil, glob
from pathlib import Path
from .utils import fail
from .partitioning import partition_and_format_disk
from .populator import populate_disk

class DiskImage:
    def __init__(self, disk):
        self.disk = disk
        self.path = f"/output/{disk['name']}.img"
        self.loopdev = None

    def create(self):
        print(f"[*] Creating disk image: {self.path}")
        os.makedirs("/output", exist_ok=True)
        subprocess.run(["truncate", "-s", self.disk["size"], self.path], check=True)

        # Force the file to be visible and synced
        with open(self.path, 'ab') as f:
            os.fsync(f.fileno())
        
        subprocess.run(["sync"], check=True)
        self.disk["_path"] = self.path

    def partition(self):
        print(f"[*] Partitioning disk: {self.disk['name']}")
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Image not found at: {self.path}")
        self.loopdev = subprocess.check_output(["losetup", "--find", "--show", self.path]).decode().strip()
        self.disk["_loopdev"] = self.loopdev
        partition_and_format_disk(self.disk)
        subprocess.run(["kpartx", "-a", self.loopdev], check=True)

    def populate(self):
        populate_disk(self.disk)

    def cleanup(self):
        if self.loopdev:
            subprocess.run(["kpartx", "-d", self.loopdev], check=True)
            subprocess.run(["losetup", "-d", self.loopdev], check=True)
        final_path = f"/output/{os.path.basename(self.path)}"
        shutil.move(self.path, final_path)
        print(f"[+] Moved disk image to: {final_path}")
