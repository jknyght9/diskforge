# Troubleshooting

Common issues and solutions when building disk images.

---

## Docker Issues

??? question "Error: `--privileged` flag required"
    DiskForge needs access to loop devices, device-mapper, and cryptsetup. Always run with `--privileged`:

    ```bash
    docker run --rm --privileged ...
    ```

    Docker Desktop on macOS and Windows supports this. On Linux, your user must be in the `docker` group or use `sudo`.

??? question "Build fails with 'output directory not writable'"
    Ensure the output directory exists and is mounted correctly:

    ```bash
    mkdir -p output
    docker run --rm --privileged \
      -v "$(pwd)/output:/output" \
      ...
    ```

??? question "Docker image build fails on ARM Mac"
    The Dockerfile supports both `amd64` and `arm64`. If you see architecture errors, ensure Docker BuildKit is enabled:

    ```bash
    DOCKER_BUILDKIT=1 docker build -t diskforge .
    ```

---

## Partition Issues

??? question "Error: 'Partition exceeds disk bounds'"
    The total size of all partitions exceeds the disk `size`. Remember to account for:

    - GPT: ~1 MiB overhead for the GPT header
    - MBR: 2048-sector (1 MiB) alignment at the start
    - Extended partitions: 1 MiB gap before the first logical partition

    **Fix:** Increase the disk `size` or reduce partition sizes.

??? question "MBR: 'Re-reading the partition table failed'"
    This is a harmless warning from `sfdisk` running inside a container. It's because the loop device can't notify the kernel of partition changes in the same way a physical disk would. `kpartx` handles the mapping instead.

---

## Filesystem Issues

??? question "exFAT mount fails"
    exFAT uses `mount.exfat-fuse` (FUSE-based). If it fails:

    - Ensure `exfat-fuse` and `exfatprogs` are installed in the container (they are by default)
    - FUSE requires `--privileged` mode
    - Check that the partition has enough space for exFAT overhead

??? question "No files matched pattern"
    The `source` glob pattern in `add_files` didn't match any files. Check that:

    - Your `files/` directory is mounted at `/files` in the container
    - The glob pattern is correct (e.g., `/files/*` not `files/*`)
    - Files actually exist at the specified path

---

## Encryption Issues

??? question "LUKS: 'Filesystem not supported for LUKS encryption'"
    LUKS only supports **ext2, ext3, ext4, and xfs**. You cannot use LUKS with FAT32, NTFS, or exFAT.

    **Fix:** Change the partition's `filesystem` to one of the supported types.

??? question "VeraCrypt: 'No such file or directory: /dev/mapper/veracrypt1'"
    This happens when the device-mapper infrastructure isn't ready in the container. DiskForge runs `dmsetup mknodes` automatically, but if you see this:

    - Ensure `--privileged` mode is enabled
    - Try running the build again (transient device-mapper timing issue)

??? question "VeraCrypt: 'NTFS signature is missing'"
    This was a bug in earlier versions where VeraCrypt tried to auto-mount a volume before the filesystem was created. Update to the latest version of DiskForge which uses `--filesystem=none` during volume creation.

??? question "VeraCrypt with wrong passphrase"
    VeraCrypt will fail silently or with a generic error when given the wrong passphrase. Unlike LUKS, there's no detectable header to confirm a volume is VeraCrypt-encrypted — this is by design (plausible deniability).

---

## Build Issues

??? question "Build succeeds but image is empty"
    Check that:

    1. Your manifest has `populate` blocks with `add_files`
    2. The `source` patterns match actual files
    3. The `/files` volume is mounted in the Docker command
    4. File operations run in order: add → copy → move → delete

??? question "Files exist but were supposed to be deleted"
    The `delete_files` paths are relative to the partition root, not the host filesystem. Use leading `/`:

    ```json
    "delete_files": ["/text1.txt"]
    ```

    Not:

    ```json
    "delete_files": ["text1.txt"]
    ```
