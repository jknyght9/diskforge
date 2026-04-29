# Compromised Workstation Scenario

An incident response training scenario where students investigate a Windows 10 workstation compromised via RDP brute force.

## Scenario Narrative

An attacker from `203.0.113.50` brute-forced RDP credentials for user `jsmith` on `WORKSTATION01` on March 15, 2025 between 02:00-04:00 UTC. After gaining access, the attacker:

1. Ran `cmd.exe` and `powershell.exe` for reconnaissance
2. Downloaded and executed `beacon.exe` (C2 implant) in the user's Temp directory
3. Installed a persistence mechanism via a service named `WindowsPerformanceMonitor`
4. Exfiltrated documents and dumped credentials to a LUKS-encrypted backup partition
5. Attempted lateral movement to `SERVER03` using stolen `admin` credentials
6. Deleted the beacon binary before disconnecting

## What Students Will Find

### Partition 1: SYSTEM (NTFS, Windows 10 template)
- **Event logs** in `Windows/System32/winevt/Logs/` — failed RDP attempts, successful logon, privilege escalation, process creation, lateral movement
- **Prefetch files** in `Windows/Prefetch/` — `BEACON.EXE`, `CMD.EXE`, `POWERSHELL.EXE`
- **Deleted malware** — `beacon.exe` was placed then deleted from `Users/jsmith/AppData/Local/Temp/` (recoverable)
- **Documents** in `Users/jsmith/Documents/` — financial reports, employee roster, network diagram

### Partition 2: BACKUP (ext4, LUKS v2 encrypted)
- Passphrase: `backup2024!`
- Contains `/staged/credentials.txt` (NTLM hashes) and `/staged/staged-data.tar.gz`

### Unallocated Space
- C2 configuration: `C2_SERVER=10.13.37.100:8443`, `BEACON_INTERVAL=60`, `EXFIL_KEY=aGVsbG8gd29ybGQ=`

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  -v "$(pwd)/output:/output" \
  diskforge /manifests/manifest.json
```

Output: `output/compromised-workstation.img` (1GB)

## Learning Objectives

- Partition table analysis with `mmls`/`fdisk`
- NTFS filesystem navigation and artifact recovery
- Windows event log analysis (Event IDs 4624, 4625, 4648, 4672, 4688)
- Prefetch file analysis
- Deleted file recovery
- LUKS encrypted volume handling
- Unallocated space analysis with `strings`/`blkls`
