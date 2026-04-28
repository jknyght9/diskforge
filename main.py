from diskforge.builder import DiskForge
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <manifest.json>")
        sys.exit(1)

    forge = DiskForge(sys.argv[1])
    forge.run()
