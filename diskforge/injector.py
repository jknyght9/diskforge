import os, sys
from .utils import fail

SECTOR_SIZE = 512
SECTORS_PER_MIB = 2048

def inject_unallocated(disk):
    """Inject data into unallocated space after the last partition."""
    inject_entries = disk.get("inject", [])
    if not inject_entries:
        return

    disk_path = disk["_path"]
    disk_size = os.path.getsize(disk_path)
    unalloc_start = _calculate_unallocated_start(disk)

    if unalloc_start >= disk_size:
        fail(f"No unallocated space on disk '{disk['name']}' — partitions fill the entire image")

    print(f"[*] Injecting data into unallocated space on {disk['name']}", file=sys.stdout, flush=True)
    print(f"    Unallocated region: byte {unalloc_start} to {disk_size} ({disk_size - unalloc_start} bytes)")

    with open(disk_path, "r+b") as img:
        for entry in inject_entries:
            data = _get_entry_data(entry)
            offset = entry.get("offset", 0)
            write_pos = unalloc_start + offset

            # Safety checks
            if write_pos < unalloc_start:
                fail(f"Inject offset {offset} would write before unallocated region")
            if write_pos + len(data) > disk_size:
                fail(f"Inject data at offset {offset} ({len(data)} bytes) exceeds disk size")

            img.seek(write_pos)
            img.write(data)
            img.flush()
            os.fsync(img.fileno())

            label = entry.get("data", entry.get("source", ""))
            if len(label) > 60:
                label = label[:60] + "..."
            print(f"    Injected {len(data)} bytes at offset {write_pos} (unalloc+{offset}): {label}")

def _get_entry_data(entry):
    """Get raw bytes from an inject entry (inline text or file source)."""
    if "data" in entry:
        return entry["data"].encode("utf-8")
    elif "source" in entry:
        with open(entry["source"], "rb") as f:
            return f.read()
    else:
        fail("Inject entry must have either 'data' or 'source'")

def _calculate_unallocated_start(disk):
    """Calculate the byte offset where unallocated space begins (after last partition)."""
    disk_type = disk["type"]

    if disk_type == "RAW":
        fail("Cannot inject into unallocated space on a RAW disk (no partition table)")

    if disk_type == "MBR":
        return _mbr_unallocated_start(disk)
    elif disk_type == "GPT":
        return _gpt_unallocated_start(disk)
    else:
        fail(f"Unknown disk type '{disk_type}' for injection")

def _mbr_unallocated_start(disk):
    """Calculate end of last partition for MBR disks using the same sector math as partitioning.py."""
    highest_end_sector = 2048  # Start after MBR + alignment

    for part in disk.get("partitions", []):
        size_mib = int(part["size"].replace("M", "").replace("G", ""))
        if "G" in part["size"]:
            size_mib *= 1024
        size_sectors = size_mib * SECTORS_PER_MIB

        if part["type"] == "extended":
            # Extended partition includes its logical partitions
            ext_size = 0
            for logical in part.get("partitions", []):
                l_size_mib = int(logical["size"].replace("M", "").replace("G", ""))
                if "G" in logical["size"]:
                    l_size_mib *= 1024
                ext_size += l_size_mib * SECTORS_PER_MIB
            # Extended has a 1MiB gap before first logical
            ext_size += SECTORS_PER_MIB
            highest_end_sector += ext_size
        else:
            highest_end_sector += size_sectors

    return highest_end_sector * SECTOR_SIZE

def _gpt_unallocated_start(disk):
    """Calculate end of last partition for GPT disks."""
    start_mib = 1  # GPT header takes 1MiB

    for part in disk.get("partitions", []):
        size_mib = int(part["size"].replace("M", "").replace("G", ""))
        if "G" in part["size"]:
            size_mib *= 1024
        start_mib += size_mib

    return start_mib * 1024 * 1024
