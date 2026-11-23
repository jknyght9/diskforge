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
            if disk.get("countermeasure"):
                _validate_countermeasures(disk["countermeasure"], disk["filesystem"], disk["name"], "raw")
            if disk.get("watermark"):
                fail(f"Watermark is not supported on RAW disk '{disk['name']}' (no partition table gap or unallocated space)")
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

            if part.get("countermeasure"):
                if disk_encrypt == "veracrypt":
                    fail(f"Countermeasures are not supported on VeraCrypt-encrypted disk '{disk['name']}'")
                _validate_countermeasures(part["countermeasure"], fs, disk["name"], part["number"])

        if disk.get("watermark"):
            if disk_encrypt == "veracrypt":
                fail(f"Watermark is not supported on VeraCrypt-encrypted disk '{disk['name']}'")
            _validate_watermark(disk["watermark"], disk["name"])

        # Validate inject entries
        for entry in disk.get("inject", []):
            if entry.get("location") != "unallocated":
                fail(f"Unsupported inject location '{entry.get('location')}' in disk '{disk['name']}'. Supported: unallocated")
            if not entry.get("data") and not entry.get("source"):
                fail(f"Inject entry in disk '{disk['name']}' must have either 'data' or 'source'")
            if entry.get("data") and entry.get("source"):
                fail(f"Inject entry in disk '{disk['name']}' cannot have both 'data' and 'source'")
            if entry.get("source") and not os.path.exists(entry["source"]):
                fail(f"Inject source file not found: {entry['source']} in disk '{disk['name']}'")
            if entry.get("offset") is not None and (not isinstance(entry["offset"], int) or entry["offset"] < 0):
                fail(f"Inject offset must be a non-negative integer in disk '{disk['name']}'")
            if disk["type"] == "RAW":
                fail(f"Cannot inject into unallocated space on RAW disk '{disk['name']}' (no partition table)")

COUNTERMEASURE_FILESYSTEMS = {
    "fat_dir_zero": ["fat32", "exfat"],
    "ntfs_index_flag": ["ntfs"],
    "ntfs_index_truncate": ["ntfs"],
}

def _validate_countermeasures(value, fs, disk_name, part_id):
    """Accept one countermeasure object or a list of them, at most one per directory."""
    cms = value if isinstance(value, list) else [value]
    if not cms or not all(isinstance(cm, dict) for cm in cms):
        fail(f"'countermeasure' in disk '{disk_name}' partition {part_id} must be an object or a list of objects")
    seen = set()
    for cm in cms:
        _validate_countermeasure(cm, fs, disk_name, part_id)
        directory = "/" + "/".join(p for p in cm.get("path", "/").split("/") if p)
        if directory in seen:
            fail(f"Disk '{disk_name}' partition {part_id} has more than one countermeasure for '{directory}'. "
                 "Use one entry per directory and list every file in its 'hide'.")
        seen.add(directory)

def _validate_countermeasure(cm, fs, disk_name, part_id):
    """Check a countermeasure block: known type, matching filesystem, directory path, file names."""
    where = f"disk '{disk_name}' partition {part_id}"
    method = cm.get("type")
    if method not in COUNTERMEASURE_FILESYSTEMS:
        fail(f"Unknown countermeasure type '{method}' in {where}. "
             f"Supported: {', '.join(COUNTERMEASURE_FILESYSTEMS)}")
    if fs.lower() not in COUNTERMEASURE_FILESYSTEMS[method]:
        fail(f"Countermeasure '{method}' requires filesystem {' or '.join(COUNTERMEASURE_FILESYSTEMS[method])}, "
             f"but {where} is '{fs}'")
    hide = cm.get("hide")
    if not hide or not isinstance(hide, list) or not all(isinstance(h, str) and h for h in hide):
        fail(f"Countermeasure in {where} requires a non-empty 'hide' list of file names")
    for h in hide:
        if "/" in h.strip("/"):
            fail(f"Countermeasure in {where}: '{h}' must be a name inside 'path', not a path")
    cm["hide"] = [h.strip("/") for h in hide]
    path = cm.get("path", "/")
    if not isinstance(path, str) or any(p in (".", "..") for p in path.split("/")):
        fail(f"Countermeasure in {where}: 'path' must be a directory path like \"/Documents\"")

def _validate_watermark(wm, disk_name):
    """Check a watermark block: owner or custom text, optional canary string, optional file flag."""
    from .watermark import build_notice, GAP_START, GAP_END
    where = f"Watermark in disk '{disk_name}'"
    if not isinstance(wm, dict):
        fail(f"{where} must be an object")
    for field in ("owner", "text", "canary"):
        if field in wm and (not isinstance(wm[field], str) or not wm[field].strip()):
            fail(f"{where}: '{field}' must be a non-empty string")
    if not wm.get("owner") and not wm.get("text"):
        fail(f"{where} requires 'owner' (used in the standard notice) or a custom 'text'")
    if "file" in wm and not isinstance(wm["file"], bool):
        fail(f"{where}: 'file' must be true or false")
    if len(build_notice(wm)[1]) > GAP_END - GAP_START:
        fail(f"{where}: notice is longer than the {GAP_END - GAP_START} bytes available before the first partition")

def _validate_template(template_name, disk_name, part_id):
    """Check that a template JSON file exists."""
    search_paths = ["/app/templates", "/templates", "templates"]
    for base in search_paths:
        path = os.path.join(base, f"{template_name}.json")
        if os.path.exists(path):
            return
    fail(f"Unknown template '{template_name}' in disk '{disk_name}' partition {part_id}. "
         f"No {template_name}.json found in templates/ directory.")
