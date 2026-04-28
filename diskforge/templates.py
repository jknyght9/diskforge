import json, os
from pathlib import Path
from .utils import fail

# Search paths for template JSON files (container paths first, then local)
TEMPLATE_SEARCH_PATHS = ["/app/templates", "/templates", "templates"]

def load_template(name):
    """Load a template JSON file by name."""
    for base in TEMPLATE_SEARCH_PATHS:
        path = os.path.join(base, f"{name}.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
    fail(f"Template '{name}' not found. Searched: {', '.join(TEMPLATE_SEARCH_PATHS)}")

def apply_template(template, mount_point):
    """Create directories and stub files defined by a template."""
    name = template.get("name", "unknown")
    mount = Path(mount_point)

    # Create directories
    for dir_path in template.get("directories", []):
        full_path = mount / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

    # Create stub files
    for file_path, spec in template.get("files", {}).items():
        full_path = mount / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        file_type = spec.get("type", "empty")
        size = spec.get("size", 0)

        if file_type == "empty":
            full_path.touch()
        elif file_type == "zero_fill":
            with open(full_path, "wb") as f:
                f.write(b'\x00' * size)
        else:
            full_path.touch()
