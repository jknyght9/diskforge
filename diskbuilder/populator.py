import glob, os, shutil, subprocess
from pathlib import Path

def populate_disk(disk):
    print(f"[*] Populating disk: {disk['name']}")
    mount_base = Path("/mnt/diskbuilder")
    os.makedirs(mount_base, exist_ok=True)

    def process_partition(part):
        if "_dev" not in part:
            return
        fs = part.get("filesystem", "").lower()
        if fs in ("", "none", "null"):
            return
        partnum = part["number"]
        mount_point = mount_base / f"{disk['name']}_part{partnum}"
        os.makedirs(mount_point, exist_ok=True)

        try:
            if fs == "exfat":
                try:
                    subprocess.run(["fuse.exfat", part["_dev"], str(mount_point)], check=True)
                except:
                    print(f"❌ Failed to mount {part['_dev']} as exfat using fuse.exfat.")
                    return
            else:
                subprocess.run(["mount", part["_dev"], str(mount_point)], check=True)
            
            populate = part.get("populate", {})

            # Add files 
            for file_entry in populate.get("add_files", []):
                target_path = mount_point / file_entry["target"].lstrip("/")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                #subprocess.run(["cp", "-av", file_entry["source"], str(target_path)], check=True)

                sources = glob.glob(file_entry["source"])
                if not sources:
                    self.fail(f"No files matched pattern: {file_entry['source']}")

                for src in sources:
                    if os.path.isdir(src):
                        subprocess.run(["cp", "-aRv", src, str(target_path)], check=True)
                    else:
                        subprocess.run(["cp", "-av", src, str(target_path)], check=True)

            # Flush all file data to disk
            subprocess.run(["sync"], check=True)

            # Copy files
            for copy in populate.get("copy_files", []):
                src_path = mount_point / copy["source"].lstrip("/")
                dst_path = mount_point / copy["target"].lstrip("/")
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                if src_path.exists():
                    shutil.copy(str(src_path), str(dst_path))

            # Flush all file and data to disk
            subprocess.run(["sync"], check=True)

            # Move files
            for move in populate.get("move_files", []):
                src_path = mount_point / move["source"].lstrip("/")
                dst_path = mount_point / move["target"].lstrip("/")
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                if src_path.exists():
                    shutil.move(str(src_path), str(dst_path))

            # Flush all file data to disk
            subprocess.run(["sync"], check=True)

            # Delete files
            for del_path in populate.get("delete_files", []):
                full_glob = str(mount_point / del_path.lstrip("/"))
                for path in glob.glob(full_glob):
                    path_obj = Path(path)
                    if path_obj.is_dir():
                        shutil.rmtree(path_obj, ignore_errors=True)
                    elif path_obj.is_file():
                        path_obj.unlink()

            # Remove empty folders
            for root, dirs, files in os.walk(mount_point, topdown=False):
                for d in dirs:
                    dir_path = Path(root) / d
                    try:
                        dir_path.rmdir()
                    except OSError:
                        pass

            # Flush all file data to disk
            subprocess.run(["sync"], check=True)

        finally:
            subprocess.run(["umount", str(mount_point)], check=True)
            os.rmdir(mount_point)

    for part in disk["partitions"]:
        if part["type"] == "extended":
            for logical in part.get("partitions", []):
                process_partition(logical)
        else:
            process_partition(part)
