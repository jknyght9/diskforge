from .manifest import load_manifest, validate_manifest
from .disk import DiskImage
from pathlib import Path
import os, subprocess, sys

class DiskForge:
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
            except Exception as e:
                print(f"[!] Failed to build disk {disk['name']}: {e}", file=sys.stderr)
                raise
            finally:
                image.cleanup()

    def clean_old_images(self):
        output_dir = Path("/output")
        output_dir.mkdir(exist_ok=True)

        # Dismount any lingering VeraCrypt volumes
        subprocess.run(["veracrypt", "--text", "--dismount", "--force"], check=False)

        # Close any lingering LUKS mappings from this tool
        if os.path.exists("/dev/mapper"):
            for dev in os.listdir("/dev/mapper"):
                if dev.startswith("luks_"):
                    print(f"[~] Closing LUKS mapping: {dev}")
                    subprocess.run(["cryptsetup", "close", dev], check=False)

        # Remove kpartx mappings and detach loop devices for our images only
        try:
            losetup_output = subprocess.check_output(["losetup", "-a"]).decode()
        except subprocess.CalledProcessError:
            losetup_output = ""

        for line in losetup_output.splitlines():
            device = line.split(":")[0]
            # Only clean up devices associated with our output images
            if "/output/" in line:
                print(f"[~] Removing kpartx mappings for: {device}")
                subprocess.run(["kpartx", "-d", device], check=False)
                print(f"[~] Detaching loop device: {device}")
                subprocess.run(["losetup", "-d", device], check=False)

        # Delete old image files
        for img in output_dir.glob("*.img"):
            print(f"[~] Removing old image: {img}")
            img.unlink(missing_ok=True)
