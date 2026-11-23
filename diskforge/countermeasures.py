import os, struct, time
from .utils import fail

# Filesystem countermeasures: hide directory entries by editing raw on-disk
# structures after the filesystem has been populated and unmounted.
#
#   fat_dir_zero        FAT32/exFAT: move hidden entries to the end of the directory
#                       and zero their first byte (end-of-directory marker)
#   ntfs_index_flag     NTFS: set the LAST_ENTRY flag on the first hidden index entry
#   ntfs_index_truncate NTFS: insert an end entry before the hidden entries and
#                       shrink the index "bytes in use" so they fall into slack

SLOT = 32  # FAT/exFAT directory entry size
NTFS_FIXUP_STRIDE = 512
INDEX_ENTRY_SUBNODE = 0x01
INDEX_ENTRY_END = 0x02
MFT_REF_MASK = 0xFFFFFFFFFFFF
NTFS_FILE_NAME_IS_DIR = 0x10000000


def split_path(path):
    return [p for p in path.split("/") if p]


def apply_countermeasure(part):
    cms = part["countermeasure"]
    if isinstance(cms, dict):
        cms = [cms]
    fs = part.get("filesystem", "").lower()
    dev = part["_dev"]

    _wait_for_release(dev)

    # Deepest directories first: hiding a folder breaks path lookups through it,
    # so anything beneath it has to be edited before it is hidden.
    ordered = sorted(cms, key=lambda cm: len(split_path(cm.get("path", "/"))), reverse=True)

    with open(dev, "r+b") as f:
        for cm in ordered:
            method, hide = cm["type"], cm["hide"]
            path = split_path(cm.get("path", "/"))
            print(f"[*] Applying countermeasure '{method}' on {dev} in /{'/'.join(path)}: hiding {', '.join(hide)}")
            if method == "fat_dir_zero" and fs == "fat32":
                _fat32_dir_zero(f, path, hide)
            elif method == "fat_dir_zero" and fs == "exfat":
                _exfat_dir_zero(f, path, hide)
            elif method in ("ntfs_index_flag", "ntfs_index_truncate") and fs == "ntfs":
                _ntfs_hide(f, path, hide, truncate=(method == "ntfs_index_truncate"))
            else:
                fail(f"Countermeasure '{method}' is not supported on filesystem '{fs}'")
        f.flush()
        os.fsync(f.fileno())


def _wait_for_release(dev, retries=50, delay=0.2):
    """FUSE drivers (ntfs-3g, exfat-fuse) keep writing after umount returns.
    Wait until no process has the device on its command line."""
    target = dev.encode()
    for _ in range(retries):
        busy = False
        for pid in os.listdir("/proc"):
            if not pid.isdigit() or int(pid) == os.getpid():
                continue
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as c:
                    if target in c.read().split(b"\0"):
                        busy = True
                        break
            except OSError:
                continue
        if not busy:
            return
        time.sleep(delay)
    fail(f"Device {dev} is still in use; cannot apply countermeasure")


# ---------------------------------------------------------------- FAT / exFAT

def _read_chain(f, fat_offset, first_cluster, mask, end_marker):
    chain, cluster = [], first_cluster
    while 2 <= cluster < end_marker:
        chain.append(cluster)
        f.seek(fat_offset + cluster * 4)
        cluster = struct.unpack("<I", f.read(4))[0] & mask
        if len(chain) > 1_000_000:
            fail("FAT chain loop detected in directory")
    return chain


def _read_dir(f, heap_offset, cluster_size, chain):
    data = bytearray()
    for c in chain:
        f.seek(heap_offset + (c - 2) * cluster_size)
        data += f.read(cluster_size)
    return data


def _write_dir(f, heap_offset, cluster_size, chain, data):
    for i, c in enumerate(chain):
        f.seek(heap_offset + (c - 2) * cluster_size)
        f.write(data[i * cluster_size:(i + 1) * cluster_size])


def _hide_groups(data, groups, hidden):
    """Rewrite the directory: visible groups first (original order), then the
    hidden groups with the first byte of every slot zeroed."""
    out = bytearray()
    for g in [g for g in groups if id(g) not in hidden] + [g for g in groups if id(g) in hidden]:
        for start in g["slots"]:
            slot = bytearray(data[start:start + SLOT])
            if id(g) in hidden:
                slot[0] = 0x00
            out += slot
    data[:len(out)] = out


def _match_hidden(groups, hide):
    wanted = {h.casefold(): h for h in hide}
    hidden = {id(g) for g in groups if g["name"] is not None and g["name"].casefold() in wanted}
    found = {g["name"].casefold() for g in groups if id(g) in hidden}
    missing = [h for k, h in wanted.items() if k not in found]
    if missing:
        fail(f"Countermeasure: file(s) not found in directory: {', '.join(missing)}")
    return hidden


def _find_subdir(groups, name):
    for g in groups:
        if g["name"] is not None and g["is_dir"] and g["name"].casefold() == name.casefold():
            return g
    fail(f"Countermeasure: directory '{name}' not found")


def _fat32_dir_zero(f, path, hide):
    f.seek(0)
    bs = f.read(512)
    bps, spc = struct.unpack_from("<HB", bs, 0x0B)
    reserved, nfats = struct.unpack_from("<HB", bs, 0x0E)
    fat_size, = struct.unpack_from("<I", bs, 0x24)
    root_cluster, = struct.unpack_from("<I", bs, 0x2C)
    fat_offset = reserved * bps
    heap_offset = (reserved + nfats * fat_size) * bps
    cluster_size = bps * spc

    def chain_from(cluster):
        return _read_chain(f, fat_offset, cluster, 0x0FFFFFFF, 0x0FFFFFF8)

    chain = chain_from(root_cluster)
    for name in path:
        sub = _find_subdir(_fat32_groups(_read_dir(f, heap_offset, cluster_size, chain)), name)
        chain = chain_from(sub["cluster"])

    data = _read_dir(f, heap_offset, cluster_size, chain)
    groups = _fat32_groups(data)
    _hide_groups(data, groups, _match_hidden(groups, hide))
    _write_dir(f, heap_offset, cluster_size, chain, data)


def _fat32_groups(data):
    """Split a FAT32 directory into entry groups: long filename slots plus their 8.3 entry."""
    groups, pending = [], []
    for start in range(0, len(data), SLOT):
        slot = data[start:start + SLOT]
        if slot[0] == 0x00:
            break
        if slot[11] == 0x0F:  # long filename slot, belongs to the next 8.3 entry
            pending.append(start)
            continue
        slots = pending + [start]
        pending = []
        name = None
        # skip deleted entries, the volume label, and the "." / ".." entries
        if slot[0] not in (0xE5, 0x2E) and not slot[11] & 0x08:
            name = _fat_lfn_name(data, slots[:-1]) or _fat_short_name(slot)
        cluster = struct.unpack_from("<H", slot, 0x14)[0] << 16 | struct.unpack_from("<H", slot, 0x1A)[0]
        groups.append({"slots": slots, "name": name, "is_dir": bool(slot[11] & 0x10), "cluster": cluster})
    if pending:
        groups.append({"slots": pending, "name": None, "is_dir": False, "cluster": 0})
    return groups


def _fat_lfn_name(data, lfn_slots):
    if not lfn_slots:
        return None
    raw = b""
    for start in reversed(lfn_slots):
        s = data[start:start + SLOT]
        raw += s[1:11] + s[14:26] + s[28:32]
    name = raw.decode("utf-16-le", errors="replace")
    return name.split("\x00")[0]


def _fat_short_name(slot):
    base = slot[0:8].decode("ascii", errors="replace").rstrip()
    ext = slot[8:11].decode("ascii", errors="replace").rstrip()
    if slot[12] & 0x08:
        base = base.lower()
    if slot[12] & 0x10:
        ext = ext.lower()
    return f"{base}.{ext}" if ext else base


def _exfat_dir_zero(f, path, hide):
    f.seek(0)
    bs = f.read(512)
    if bs[3:11] != b"EXFAT   ":
        fail("Countermeasure: device is not exFAT")
    fat_offset_sectors, = struct.unpack_from("<I", bs, 0x50)
    heap_offset_sectors, = struct.unpack_from("<I", bs, 0x58)
    root_cluster, = struct.unpack_from("<I", bs, 0x60)
    bps = 1 << bs[0x6C]
    cluster_size = bps << bs[0x6D]
    fat_offset = fat_offset_sectors * bps
    heap_offset = heap_offset_sectors * bps

    chain = _read_chain(f, fat_offset, root_cluster, 0xFFFFFFFF, 0xFFFFFFF8)
    for name in path:
        sub = _find_subdir(_exfat_groups(_read_dir(f, heap_offset, cluster_size, chain)), name)
        if sub["no_fat_chain"]:  # contiguous allocation, the FAT is not maintained
            count = -(-sub["length"] // cluster_size)
            chain = list(range(sub["cluster"], sub["cluster"] + count))
        else:
            chain = _read_chain(f, fat_offset, sub["cluster"], 0xFFFFFFFF, 0xFFFFFFF8)

    data = _read_dir(f, heap_offset, cluster_size, chain)
    groups = _exfat_groups(data)
    _hide_groups(data, groups, _match_hidden(groups, hide))
    _write_dir(f, heap_offset, cluster_size, chain, data)


def _exfat_groups(data):
    """Split an exFAT directory into entry sets: a primary entry plus its secondaries."""
    groups = []
    for start in range(0, len(data), SLOT):
        etype = data[start]
        if etype == 0x00:
            break
        if etype & 0x40 and groups:  # secondary entry, belongs to the current set
            groups[-1]["slots"].append(start)
        else:
            groups.append({"slots": [start], "type": etype})

    for g in groups:
        g.update(name=None, is_dir=False, cluster=0, length=0, no_fat_chain=False)
        if g["type"] != 0x85:  # only in-use File entry sets: File, Stream Extension, File Name...
            continue
        slots = [data[s:s + SLOT] for s in g["slots"]]
        stream = [s for s in slots if s[0] == 0xC0]
        names = [s for s in slots if s[0] == 0xC1]
        if not stream:
            continue
        raw = b"".join(s[2:32] for s in names)
        g["name"] = raw.decode("utf-16-le", errors="replace")[:stream[0][3]]
        g["is_dir"] = bool(struct.unpack_from("<H", slots[0], 4)[0] & 0x10)
        g["no_fat_chain"] = bool(stream[0][1] & 0x02)
        g["cluster"], = struct.unpack_from("<I", stream[0], 0x14)
        g["length"], = struct.unpack_from("<Q", stream[0], 0x18)
    return groups


# ---------------------------------------------------------------------- NTFS

def _ntfs_unfix(rec, magic):
    if rec[0:4] != magic:
        fail(f"Countermeasure: bad NTFS record signature {bytes(rec[0:4])!r}, expected {magic!r}")
    usa_ofs, usa_count = struct.unpack_from("<HH", rec, 4)
    usn = rec[usa_ofs:usa_ofs + 2]
    for i in range(1, usa_count):
        end = i * NTFS_FIXUP_STRIDE - 2
        if rec[end:end + 2] != usn:
            fail("Countermeasure: NTFS fixup mismatch (record is torn or corrupt)")
        rec[end:end + 2] = rec[usa_ofs + i * 2:usa_ofs + i * 2 + 2]


def _ntfs_fix(rec):
    usa_ofs, usa_count = struct.unpack_from("<HH", rec, 4)
    usn = rec[usa_ofs:usa_ofs + 2]
    for i in range(1, usa_count):
        end = i * NTFS_FIXUP_STRIDE - 2
        rec[usa_ofs + i * 2:usa_ofs + i * 2 + 2] = rec[end:end + 2]
        rec[end:end + 2] = usn


def _ntfs_record_size(value, cluster_size):
    value = struct.unpack("<b", bytes([value]))[0]
    return cluster_size * value if value > 0 else 1 << -value


def _ntfs_attrs(rec):
    pos, = struct.unpack_from("<H", rec, 0x14)
    attrs = {}
    while pos + 8 <= len(rec):
        atype, alen = struct.unpack_from("<II", rec, pos)
        if atype == 0xFFFFFFFF or alen == 0:
            break
        name_len, name_ofs = rec[pos + 9], struct.unpack_from("<H", rec, pos + 0x0A)[0]
        name = rec[pos + name_ofs:pos + name_ofs + name_len * 2].decode("utf-16-le")
        attrs.setdefault((atype, name), pos)
        pos += alen
    return attrs


def _ntfs_runlist(rec, attr_pos):
    pos = attr_pos + struct.unpack_from("<H", rec, attr_pos + 0x20)[0]
    runs, vcn, lcn = [], 0, 0
    while rec[pos] != 0:
        len_size, ofs_size = rec[pos] & 0x0F, rec[pos] >> 4
        length = int.from_bytes(rec[pos + 1:pos + 1 + len_size], "little")
        delta = int.from_bytes(rec[pos + 1 + len_size:pos + 1 + len_size + ofs_size], "little", signed=True)
        lcn += delta
        runs.append((vcn, lcn if ofs_size else None, length))
        vcn += length
        pos += 1 + len_size + ofs_size
    return runs


def _ntfs_map(runs, byte_in_attr, length, cluster_size):
    """Translate a byte offset inside a non-resident attribute to a device offset."""
    cluster, within = divmod(byte_in_attr, cluster_size)
    for run_vcn, run_lcn, run_len in runs:
        if run_vcn <= cluster < run_vcn + run_len and run_lcn is not None:
            if (cluster - run_vcn) * cluster_size + within + length > run_len * cluster_size:
                fail("Countermeasure: NTFS record spans a fragmented run")
            return (run_lcn + cluster - run_vcn) * cluster_size + within
    fail("Countermeasure: NTFS attribute offset not mapped")


def _ntfs_entries(buf, node):
    """Walk the index entries of the node header at `node`, up to and including END."""
    entries_ofs, in_use = struct.unpack_from("<II", buf, node)
    pos, entries = node + entries_ofs, []
    while pos < node + in_use:
        ref, length, key_len, flags = struct.unpack_from("<QHHH", buf, pos)
        e = {"pos": pos, "length": length, "flags": flags, "ref": ref & MFT_REF_MASK, "name": None, "is_dir": False}
        if not flags & INDEX_ENTRY_END and key_len >= 0x42:
            key = pos + 0x10
            name_len = buf[key + 0x40]
            e["name"] = buf[key + 0x42:key + 0x42 + name_len * 2].decode("utf-16-le")
            e["is_dir"] = bool(struct.unpack_from("<I", buf, key + 0x38)[0] & NTFS_FILE_NAME_IS_DIR)
        entries.append(e)
        if flags & INDEX_ENTRY_END:
            return entries
        pos += length
    fail("Countermeasure: NTFS index has no end entry")


def _ntfs_volume(f):
    f.seek(0)
    bs = f.read(512)
    if bs[3:11] != b"NTFS    ":
        fail("Countermeasure: device is not NTFS")
    bps, spc = struct.unpack_from("<HB", bs, 0x0B)
    vol = {"cluster_size": bps * spc}
    vol["rec_size"] = _ntfs_record_size(bs[0x40], vol["cluster_size"])
    mft_lcn, = struct.unpack_from("<Q", bs, 0x30)

    # $MFT (record 0) describes where the rest of the MFT lives
    f.seek(mft_lcn * vol["cluster_size"])
    mft = bytearray(f.read(vol["rec_size"]))
    _ntfs_unfix(mft, b"FILE")
    vol["mft_runs"] = _ntfs_runlist(mft, _ntfs_attrs(mft)[(0x80, "")])
    return vol


def _ntfs_leaf(f, vol, mft_num):
    """Locate the single leaf node of a directory's $I30 index.

    Supported layouts: the entries are resident in $INDEX_ROOT (small directory),
    or $INDEX_ROOT holds only an END entry pointing at one leaf INDX block.
    Returns (unfixed buffer, node header offset, device offset of the buffer)."""
    rec_off = _ntfs_map(vol["mft_runs"], mft_num * vol["rec_size"], vol["rec_size"], vol["cluster_size"])
    f.seek(rec_off)
    rec = bytearray(f.read(vol["rec_size"]))
    _ntfs_unfix(rec, b"FILE")

    attrs = _ntfs_attrs(rec)
    if (0x90, "$I30") not in attrs:
        fail(f"Countermeasure: NTFS MFT record {mft_num} is not a directory")
    ir = attrs[(0x90, "$I30")]
    ir_value = ir + struct.unpack_from("<H", rec, ir + 0x14)[0]
    block_size, = struct.unpack_from("<I", rec, ir_value + 8)
    root_node = ir_value + 0x10
    root_entries = _ntfs_entries(rec, root_node)

    if not rec[root_node + 12] & 0x01:  # small index, entries live in the MFT record
        return rec, root_node, rec_off

    if (0xA0, "$I30") not in attrs or len(root_entries) != 1 or not root_entries[0]["flags"] & INDEX_ENTRY_SUBNODE:
        fail("Countermeasure: NTFS directory index has more than one level (too many files in directory)")
    end = root_entries[0]
    leaf_vcn, = struct.unpack_from("<Q", rec, end["pos"] + end["length"] - 8)
    vcn_size = vol["cluster_size"] if block_size >= vol["cluster_size"] else 512
    runs = _ntfs_runlist(rec, attrs[(0xA0, "$I30")])
    indx_off = _ntfs_map(runs, leaf_vcn * vcn_size, block_size, vol["cluster_size"])

    f.seek(indx_off)
    indx = bytearray(f.read(block_size))
    _ntfs_unfix(indx, b"INDX")
    if indx[0x18 + 12] & 0x01:
        fail("Countermeasure: NTFS directory index has more than one level (too many files in directory)")
    return indx, 0x18, indx_off


def _ntfs_hide(f, path, hide, truncate):
    vol = _ntfs_volume(f)

    mft_num = 5  # root directory
    for name in path:
        buf, node, _ = _ntfs_leaf(f, vol, mft_num)
        match = [e for e in _ntfs_entries(buf, node) if e["name"] == name and e["is_dir"]]
        if not match:
            fail(f"Countermeasure: directory '{name}' not found")
        mft_num = match[0]["ref"]

    buf, node, disk_off = _ntfs_leaf(f, vol, mft_num)
    entries = _ntfs_entries(buf, node)
    files, end = entries[:-1], entries[-1]

    by_name = {e["name"]: e["ref"] for e in files if e["name"] is not None}
    missing = [h for h in hide if h not in by_name]
    if missing:
        fail(f"Countermeasure: file(s) not found in NTFS directory: {', '.join(missing)}")
    hidden_refs = {by_name[h] for h in hide}
    first = next(i for i, e in enumerate(files) if e["ref"] in hidden_refs)
    after = [e["name"] for e in files[first:] if e["ref"] not in hidden_refs]
    if after:
        fail(f"Countermeasure: NTFS index is sorted by name; these visible files sort after a hidden one: "
             f"{', '.join(after)}. Rename the hidden files so they sort last.")

    cut = files[first]["pos"]
    if truncate:
        # Shift the hidden entries over the old 16-byte END entry, write a new END
        # at the cut, and shrink bytes-in-use so the hidden entries become slack.
        end_pos = end["pos"]
        buf[cut + 16:end_pos + 16] = buf[cut:end_pos]
        buf[cut:cut + 16] = struct.pack("<QHHHH", 0, 16, 0, INDEX_ENTRY_END, 0)
        struct.pack_into("<I", buf, node + 4, cut + 16 - node)
    else:
        flags, = struct.unpack_from("<H", buf, cut + 12)
        struct.pack_into("<H", buf, cut + 12, flags | INDEX_ENTRY_END)

    _ntfs_fix(buf)
    f.seek(disk_off)
    f.write(buf)
