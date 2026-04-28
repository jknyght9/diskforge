# OS Templates

Templates create realistic operating system directory structures with placeholder files on your disk images. They're applied before file population, so scenario-specific evidence files can be placed directly into the correct OS paths.

---

## Using Templates

Add a `template` field to the `populate` block of any partition:

```json
{
  "number": 1,
  "type": "primary",
  "filesystem": "ntfs",
  "label": "SYSTEM",
  "size": "2G",
  "populate": {
    "template": "windows10",
    "add_files": [
      { "source": "/files/evtx/*", "target": "/Windows/System32/winevt/Logs" },
      { "source": "/files/prefetch/*", "target": "/Windows/Prefetch" },
      { "source": "/files/registry/*", "target": "/Windows/System32/config" }
    ]
  }
}
```

The template creates the directory structure and stub files first, then `add_files` overlays your scenario evidence into the existing structure.

---

## Available Templates

### windows10

Windows 10/11 NTFS structure. Recommended filesystem: `ntfs`

**Key directories:**

| Path | Forensic Relevance |
|------|-------------------|
| `Windows/System32/config` | Registry hives (SAM, SYSTEM, SOFTWARE, SECURITY) |
| `Windows/System32/winevt/Logs` | Windows Event Logs (EVTX) |
| `Windows/Prefetch` | Application prefetch files |
| `Windows/appcompat/Programs` | Amcache.hve |
| `Windows/System32/sru` | SRUM database |
| `Users/Default/AppData/Roaming/Microsoft/Windows/Recent` | Recent files (LNK) |
| `Users/Default/AppData/Local/Microsoft/Windows/Explorer` | Shellbags |
| `$Recycle.Bin` | Deleted files |

**Stub files created:** SAM, SYSTEM, SOFTWARE, SECURITY, DEFAULT, NTUSER.DAT, Amcache.hve, SRUDB.dat, bootmgr, pagefile.sys, hiberfil.sys, cmd.exe, powershell.exe, explorer.exe

### windowsxp

Windows XP/2003 structure. Recommended filesystem: `ntfs`

**Key differences from Windows 10:**

- Uses `WINDOWS` instead of `Windows`
- Uses `Documents and Settings` instead of `Users`
- Uses `Recycled` instead of `$Recycle.Bin`
- Includes `ntldr`, `NTDETECT.COM`, `boot.ini`

### linux

Linux FHS (Filesystem Hierarchy Standard). Recommended filesystem: `ext4`

**Key directories:**

| Path | Forensic Relevance |
|------|-------------------|
| `var/log` | System logs (syslog, auth.log, kern.log) |
| `var/log/journal` | systemd journal |
| `etc/ssh` | SSH configuration |
| `etc/cron.d`, `var/spool/cron` | Scheduled tasks |
| `root/.ssh` | Root SSH keys |
| `root/.bash_history` | Command history |

**Stub files created:** passwd, shadow, group, hostname, hosts, fstab, crontab, sshd_config, syslog, auth.log, kern.log, wtmp, btmp, lastlog, .bash_history, .bashrc

### macos

macOS HFS+ structure. Recommended filesystem: `hfsplus`

**Key directories:**

| Path | Forensic Relevance |
|------|-------------------|
| `private/var/log` | System logs |
| `private/var/db` | System databases |
| `Library/LaunchAgents` | User-level persistence |
| `System/Library/LaunchDaemons` | System-level persistence |
| `.fseventsd` | FSEvents (file system activity) |
| `.Spotlight-V100` | Spotlight index |

**Stub files created:** passwd, hosts, system.log, install.log, wifi.log, .AppleSetupDone, SystemVersion.plist, fseventsd-uuid, Spotlight store.db

---

## Template Format

Templates are JSON files stored in the `templates/` directory:

```json
{
  "name": "windows10",
  "description": "Windows 10/11 NTFS directory structure",
  "recommended_filesystem": "ntfs",
  "directories": [
    "Windows/System32",
    "Windows/System32/config",
    "Windows/Prefetch"
  ],
  "files": {
    "Windows/System32/config/SAM": { "type": "empty" },
    "pagefile.sys": { "type": "zero_fill", "size": 4096 }
  }
}
```

### File Types

| Type | Description |
|------|-------------|
| `empty` | Creates a 0-byte placeholder file |
| `zero_fill` | Creates a file filled with null bytes of the specified `size` |

---

## Custom Templates

Create your own template by adding a JSON file to the `templates/` directory. Mount custom templates into the container:

```bash
docker run --rm --privileged \
  -v "$(pwd)/my-templates:/templates" \
  -v "$(pwd)/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/output:/output" \
  diskforge /manifests/manifest.json
```

!!! tip "Template Design Tips"
    - Include directories that are forensically relevant (log paths, config locations, persistence mechanisms)
    - Use `empty` stub files for registry hives, databases, and executables — they create the right paths for students to recognize
    - Use `zero_fill` for files like `pagefile.sys` that should have some size but don't need real content
    - Templates + `add_files` is powerful: the template creates the structure, then you inject real evidence files (EVTX, prefetch, registry exports) into specific locations

---

## Example: Windows Forensic Scenario

```json
{
  "disks": [{
    "name": "suspect-workstation",
    "type": "MBR",
    "size": "1G",
    "bootable": true,
    "partitions": [{
      "number": 1,
      "type": "primary",
      "filesystem": "ntfs",
      "label": "SYSTEM",
      "size": "900M",
      "populate": {
        "template": "windows10",
        "add_files": [
          { "source": "/files/evtx/*.evtx", "target": "/Windows/System32/winevt/Logs" },
          { "source": "/files/prefetch/*.pf", "target": "/Windows/Prefetch" },
          { "source": "/files/registry/NTUSER.DAT", "target": "/Users/Default" },
          { "source": "/files/suspect-docs/*", "target": "/Users/Default/Documents" }
        ],
        "delete_files": [
          "/Users/Default/Documents/financial_records.xlsx"
        ]
      }
    }]
  }]
}
```

Students receive a disk image that looks like a real Windows system, with planted evidence in the correct forensic locations and a deleted file to recover.
