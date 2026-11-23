from diskforge.builder import DiskForge
from diskforge.manifest import load_manifest, validate_manifest
import sys

if __name__ == "__main__":
    args = sys.argv[1:]
    validate_only = "--validate" in args
    args = [a for a in args if a != "--validate"]
    if len(args) < 1:
        print("Usage: python main.py [--validate] <manifest.json>")
        sys.exit(1)

    if validate_only:
        validate_manifest(load_manifest(args[0]))
        print("Manifest OK")
        sys.exit(0)

    forge = DiskForge(args[0])
    forge.run()
