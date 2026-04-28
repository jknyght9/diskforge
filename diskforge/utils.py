import sys, time
from pathlib import Path

def fail(message):
    print(f"❌ {message}")
    sys.exit(1)

def wait_for_device(path, retries=10, delay=0.5):
    for _ in range(retries):
        if Path(path).exists():
            return True
        time.sleep(delay)
    raise RuntimeError(f"Timeout waiting for device: {path}")
