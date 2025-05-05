from .manifest import load_manifest, validate_manifest
from .disk import DiskImage
from pathlib import Path
import os, shutil, subprocess, sys

class DiskBuilder:
    def __init__(self, manifest_path):
        self.manifest_path = manifest_path
        self.disks = []

    def run(self):
        self.clean_old_images()
        self.disks = load_manifest(self.manifest_path)
        validate_manifest(self.disks)

        for disk in self.disks:
            image = DiskImage(disk)

            try:
                image.create()
                image.partition()
                image.populate()
                image.cleanup()
            except Exception as e:
                print(f"[!] Failed to build disk {disk['name']}: {e}", file=sys.stderr)

    def clean_old_images(self):
        output_dir = Path("/output")
        output_dir.mkdir(exist_ok=True)

        # Step 1: Unmount and close veracrypt volumes
        subprocess.run(["veracrypt", "--text", "--dismount", "--force"], check=False)

        # Step 2: Close all LUKS mappings
        for dev in os.listdir("/dev/mapper"):
            if dev.startswith("luks_"):
                print(f"[~] Closing LUKS mapping: {dev}")
                subprocess.run(["cryptsetup", "close", dev], check=False)

        # Step 3: Remove all kpartx mappings
        losetup_output = subprocess.check_output(["losetup", "-a"]).decode()
        for line in losetup_output.splitlines():
            device = line.split(":")[0]
            if "training_" in line or "example_" in line:
                print(f"[~] Removing kpartx mappings for: {device}")
                subprocess.run(["kpartx", "-d", device], check=False)

        # Step 4: Detach all stale loop devices
        for line in losetup_output.splitlines():
            device = line.split(":")[0]
            if "training_" in line or "example_" in line:
                print(f"[~] Detaching loop device: {device}")
                subprocess.run(["losetup", "-d", device], check=False)

        # Step 5: Delete old image files
        for img in output_dir.glob("*.img"):
            print(f"[~] Removing old image: {img}")
            img.unlink(missing_ok=True)
