from .manifest import load_manifest, validate_manifest
from .disk import DiskImage
from pathlib import Path
import shutil, subprocess

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
            image.create()
            image.partition()
            image.populate()
            image.cleanup()

    def clean_old_images(self):
        output_dir = Path("/output")
        output_dir.mkdir(exist_ok=True)
        for img in output_dir.glob("*.img"):
            print(f"[~] Removing old image: {img}")
            img.unlink()
