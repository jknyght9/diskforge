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
    for disk in disks:
        for field in ["name", "type", "size", "partitions"]:
            if field not in disk:
                fail(f"Missing required disk field '{field}'")
        if disk["type"] not in ["MBR", "GPT"]:
            fail(f"Invalid disk type '{disk['type']}'")

        for part in disk["partitions"]:
            for field in ["number", "type", "filesystem", "size"]:
                if field not in part:
                    fail(f"Missing required partition field '{field}' in disk '{disk['name']}' partition {part['number']}")
            for file_entry in part.get("populate", {}).get("add_files", []):
                if not glob.glob(file_entry["source"]):
                    fail(f"No matching files for pattern: {file_entry['source']}")
