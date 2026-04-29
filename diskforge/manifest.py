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
    supported_luks_filesystems = ["ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs"]

    for disk in disks:
        for field in ["name", "type", "size"]:
            if field not in disk:
                fail(f"Missing required disk field '{field}'")

        if disk["type"] not in ["MBR", "GPT", "RAW"]:
            fail(f"Invalid disk type '{disk['type']}'")

        # RAW disk validation — no partitions, filesystem at disk level
        if disk["type"] == "RAW":
            if disk.get("partitions"):
                fail(f"RAW disk '{disk['name']}' must not have a 'partitions' array")
            if not disk.get("filesystem"):
                fail(f"RAW disk '{disk['name']}' requires a 'filesystem' field")
            # Validate populate add_files globs
            for file_entry in disk.get("populate", {}).get("add_files", []):
                if not glob.glob(file_entry["source"]):
                    fail(f"No matching files for pattern: {file_entry['source']}")
            # Validate template if specified
            template_name = disk.get("populate", {}).get("template")
            if template_name:
                _validate_template(template_name, disk["name"], "raw")
            continue

        # MBR/GPT disks require partitions
        if "partitions" not in disk:
            fail(f"Missing required disk field 'partitions'")

        # Validate boot_code path if provided
        if disk.get("boot_code"):
            boot_path = disk["boot_code"]
            if not os.path.exists(boot_path):
                fail(f"Boot code file not found: {boot_path} in disk '{disk['name']}'")

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
                    fail(f"Missing required partition field '{field}' in disk '{disk['name']}' partition {part.get('number', '?')}")

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

                if enc_type == "luks" and fs not in supported_luks_filesystems:
                    fail(f"Filesystem '{fs}' not supported for LUKS encryption in disk '{disk['name']}' partition {part['number']}. Supported: {', '.join(supported_luks_filesystems)}")

            # Validate populate add_files globs
            for file_entry in part.get("populate", {}).get("add_files", []):
                if not glob.glob(file_entry["source"]):
                    fail(f"No matching files for pattern: {file_entry['source']}")

            # Validate template if specified
            template_name = part.get("populate", {}).get("template")
            if template_name:
                _validate_template(template_name, disk["name"], part["number"])

def _validate_template(template_name, disk_name, part_id):
    """Check that a template JSON file exists."""
    search_paths = ["/app/templates", "/templates", "templates"]
    for base in search_paths:
        path = os.path.join(base, f"{template_name}.json")
        if os.path.exists(path):
            return
    fail(f"Unknown template '{template_name}' in disk '{disk_name}' partition {part_id}. "
         f"No {template_name}.json found in templates/ directory.")
