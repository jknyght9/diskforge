from diskbuilder.builder import DiskBuilder
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <manifest.json>")
        sys.exit(1)

    builder = DiskBuilder(sys.argv[1])
    builder.run()
