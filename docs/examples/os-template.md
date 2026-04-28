# Example: OS Template

A GPT disk using the Windows 10 template to create a realistic directory structure, then overlaying scenario files.

---

## Manifest

```json
{
  "schema_version": "1.0",
  "disks": [
    {
      "name": "training_template",
      "label": "TemplateExample",
      "type": "GPT",
      "size": "256M",
      "bootable": true,
      "partitions": [
        {
          "number": 1,
          "type": "primary",
          "filesystem": "ntfs",
          "label": "SYSTEM",
          "size": "250M",
          "populate": {
            "template": "windows10",
            "add_files": [
              { "source": "/files/*", "target": "/Users/Default/Documents" }
            ],
            "delete_files": ["/Users/Default/Documents/text1.txt"]
          }
        }
      ]
    }
  ]
}
```

## Build

```bash
docker run --rm --privileged \
  -v "$(pwd)/examples/example_template:/output" \
  -v "$(pwd)/examples/example_template/manifest.json:/manifests/manifest.json" \
  -v "$(pwd)/files:/files" \
  diskforge /manifests/manifest.json
```

## What's Created

The Windows 10 template creates this structure before files are added:

```
/
├── Windows/
│   ├── System32/
│   │   ├── config/
│   │   │   ├── SAM           (stub)
│   │   │   ├── SYSTEM        (stub)
│   │   │   ├── SOFTWARE      (stub)
│   │   │   └── SECURITY      (stub)
│   │   ├── winevt/Logs/
│   │   ├── drivers/etc/hosts  (stub)
│   │   └── sru/SRUDB.dat     (stub)
│   ├── Prefetch/
│   ├── Temp/
│   ├── appcompat/Programs/Amcache.hve  (stub)
│   ├── bootmgr                (stub)
│   └── explorer.exe           (stub)
├── Program Files/
├── Program Files (x86)/
├── Users/
│   ├── Default/
│   │   ├── Documents/         ← scenario files placed here
│   │   ├── Desktop/
│   │   ├── Downloads/
│   │   └── NTUSER.DAT        (stub)
│   └── Public/
├── $Recycle.Bin/
├── pagefile.sys               (4KB zero-fill)
├── hiberfil.sys               (4KB zero-fill)
└── $MFT                       (stub)
```

Then `add_files` places the scenario evidence into `/Users/Default/Documents`, and `delete_files` removes `text1.txt` for a recovery exercise.

## What Students Learn

- Navigating a realistic Windows directory structure in a forensic image
- Finding registry hives at the expected paths
- Identifying forensically relevant directories (Prefetch, winevt, Amcache)
- Understanding that real OS images are much larger but follow the same structure
