import json, os, glob
from .utils import fail

def load_manifest(path):
    if not os.path.exists(path):
        fail(f"Manifest file not found: {path}")
    with open(path) as f:
        manifest = json.load(f)
    if 'disks' not in manifest:
        fail("Manifest must contain a 'disks' array")
    return manifest['disks']

def validate_manifest(disks):
    supported_luks_filesystems = ["ext2", "ext3", "ext4", "xfs"]

    for disk in disks:
        for field in ["name", "type", "size", "partitions"]:
            if field not in disk:
                fail(f"Missing required disk field '{field}'")

        if disk["type"] not in ["MBR", "GPT"]:
            fail(f"Invalid disk type '{disk['type']}'")

        disk_encrypt = disk.get("encrypt", {}).get("type")
        partitions = disk.get("partitions", [])

        # VeraCrypt full-disk encryption validation
        if disk_encrypt == "veracrypt":
            if len(partitions) > 1:
                fail(
                    f"Disk '{disk['name']}' uses VeraCrypt full-disk encryption but has multiple partitions. "
                    "Only one placeholder partition is allowed."
                )
            for part in partitions:
                part_encrypt = part.get("encrypt", {}).get("type")
                if part_encrypt == "veracrypt":
                    fail(
                        f"Partition-level VeraCrypt encryption is not allowed. "
                        f"Disk '{disk['name']}' is already VeraCrypt-encrypted."
                    )

        elif disk_encrypt != "veracrypt":
            for part in partitions:
                part_encrypt = part.get("encrypt", {}).get("type")
                if part_encrypt == "veracrypt":
                    fail(
                        f"VeraCrypt encryption is only supported at the disk level. "
                        f"Disk '{disk['name']}' has partition-level VeraCrypt."
                    )

        for part in disk["partitions"]:
            for field in ["number", "type", "filesystem", "size"]:
                if field not in part:
                    fail(f"Missing required partition field '{field}' in disk '{disk['name']}' partition {part['number']}")

            fs = part["filesystem"]
            encrypt_cfg = part.get("encrypt")
            
            # Skip filesystem checks for extended partitions
            if part["type"] == "extended":
                if encrypt_cfg:
                    fail(f"Encryption should not be applied to extended partition {part['number']} in disk '{disk['name']}'")
                continue

            if not isinstance(fs, str):
                fail(f"Invalid or missing filesystem for partition {part['number']} in disk '{disk['name']}'")

            fs_lower = fs.lower()

            if encrypt_cfg:
                enc_type = encrypt_cfg.get("type")
                passphrase = encrypt_cfg.get("passphrase")

                if enc_type not in ["luks", "veracrypt"]:
                    fail(f"Unsupported encryption type '{enc_type}' in disk '{disk['name']}' partition {part['number']}")

                if not passphrase or not isinstance(passphrase, str):
                    fail(f"Encryption passphrase is missing or invalid in disk '{disk['name']}' partition {part['number']}")

                # ✅ LUKS-specific filesystem enforcement
                if enc_type == "luks" and fs not in supported_luks_filesystems:
                    fail(f"Filesystem '{fs}' not supported for LUKS encryption in disk '{disk['name']}' partition {part['number']}. Supported: {', '.join(supported_luks_filesystems)}")
            for file_entry in part.get("populate", {}).get("add_files", []):
                if not glob.glob(file_entry["source"]):
                    fail(f"No matching files for pattern: {file_entry['source']}")
