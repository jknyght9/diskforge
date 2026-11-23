"""DiskForge MCP server: validate and build manifests through the diskforge Docker image.

Runs on the host and starts one container per call, so the privileged container stays exactly
as `docker run` uses it today. Building only: there are no tools that inspect built images.
"""
import json, os, re, subprocess
from pathlib import Path
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

REPO = Path(__file__).resolve().parent.parent
IMAGE = os.environ.get("DISKFORGE_IMAGE", "diskforge")
BUILD_TIMEOUT = 1800
LOG_TAIL = 60
DOCS = {
    "manifest-reference": "configuration/manifest-reference.md",
    "encryption": "configuration/encryption.md",
    "templates": "configuration/templates.md",
    "injection": "configuration/injection.md",
    "countermeasures": "configuration/countermeasures.md",
    "watermark": "configuration/watermark.md",
}

server = MCPServer(
    "diskforge",
    instructions=(
        "DiskForge builds forensics training disk images from JSON manifests. Read the "
        "diskforge://docs/manifest-reference resource before writing a manifest. Inside a manifest, "
        "file sources are container paths under /files (the files_dir on the host). Run "
        "validate_manifest before build."
    ),
)

def _resolve(path):
    p = Path(path).expanduser()
    return (p if p.is_absolute() else REPO / p).resolve()

def _docker(args, timeout):
    try:
        r = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "docker not found on PATH"
    except subprocess.TimeoutExpired:
        return 124, f"docker timed out after {timeout} seconds"
    return r.returncode, r.stdout + r.stderr

def _check_inputs(manifest_path, files_dir):
    manifest, files = _resolve(manifest_path), _resolve(files_dir)
    if not manifest.is_file():
        return None, None, f"Manifest not found: {manifest}"
    if not files.is_dir():
        return None, None, f"files_dir not found: {files}"
    code, _ = _docker(["image", "inspect", IMAGE], 30)
    if code != 0:
        return None, None, f"Docker image '{IMAGE}' not found. Build it with: docker build -t {IMAGE} {REPO}"
    return manifest, files, None

@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def validate_manifest(manifest_path: str, files_dir: str = "files") -> dict:
    """Validate a manifest in the diskforge container without building anything.

    Paths are on the host; relative paths resolve against the DiskForge repo. files_dir is mounted
    at /files, so add_files globs and inject sources are checked against it.
    """
    manifest, files, error = _check_inputs(manifest_path, files_dir)
    if error:
        return {"ok": False, "error": error}
    code, out = _docker(["run", "--rm", "-v", f"{files}:/files", "-v", f"{manifest}:/manifests/manifest.json",
                         IMAGE, "--validate", "/manifests/manifest.json"], 120)
    return {"ok": code == 0, "output": out.strip()}

@server.tool(annotations=ToolAnnotations(destructive_hint=True))
def build(manifest_path: str, files_dir: str = "files", output_dir: str = "",
          replace_other_images: bool = False) -> dict:
    """Build every disk in a manifest. Takes minutes; runs a privileged container.

    output_dir defaults to the manifest's directory. DiskForge deletes every .img in output_dir
    before building, so the call refuses when output_dir holds images this manifest does not
    produce, unless replace_other_images is true. Returns the built images with their sizes,
    any watermark canary GUIDs, and the end of the build log.
    """
    manifest, files, error = _check_inputs(manifest_path, files_dir)
    if error:
        return {"ok": False, "error": error}
    output = _resolve(output_dir) if output_dir else manifest.parent
    output.mkdir(parents=True, exist_ok=True)

    try:
        names = [d["name"] for d in json.loads(manifest.read_text()).get("disks", [])]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return {"ok": False, "error": f"Manifest is not valid DiskForge JSON: {e}"}
    others = sorted(p.name for p in output.glob("*.img") if p.stem not in names)
    if others and not replace_other_images:
        return {"ok": False, "error": f"output_dir {output} holds images this build would delete: "
                                      f"{', '.join(others)}. Use another output_dir or set replace_other_images."}

    code, out = _docker(["run", "--rm", "--privileged", "-v", f"{files}:/files",
                         "-v", f"{manifest}:/manifests/manifest.json", "-v", f"{output}:/output",
                         IMAGE, "/manifests/manifest.json"], BUILD_TIMEOUT)
    images = [{"path": str(output / f"{n}.img"), "bytes": (output / f"{n}.img").stat().st_size}
              for n in names if (output / f"{n}.img").exists()]
    canaries = dict(re.findall(r"Watermark for (\S+): canary GUID (\S+)", out))
    return {"ok": code == 0 and len(images) == len(names), "exit_code": code, "images": images,
            "canaries": canaries, "log_tail": "\n".join(out.splitlines()[-LOG_TAIL:])}

@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_templates() -> list[dict]:
    """List OS templates usable as populate.template, with their descriptions."""
    result = []
    for p in sorted((REPO / "templates").glob("*.json")):
        t = json.loads(p.read_text())
        result.append({"name": p.stem, "description": t.get("description", ""),
                       "recommended_filesystem": t.get("recommended_filesystem", "")})
    return result

@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def list_examples() -> list[dict]:
    """List the example manifests shipped with DiskForge, with each disk's type, size, and features."""
    result = []
    for p in sorted((REPO / "examples").glob("*/manifest.json")):
        disks = []
        for d in json.loads(p.read_text()).get("disks", []):
            parts = [d] + [q for p in d.get("partitions", []) for q in [p, *p.get("partitions", [])]]
            features = [k for k in ("encrypt", "boot_code", "inject", "watermark", "countermeasure")
                        if any(x.get(k) for x in parts)]
            features += sorted({x["populate"]["template"] for x in parts if x.get("populate", {}).get("template")})
            disks.append({"name": d["name"], "type": d["type"], "size": d["size"], "features": features})
        result.append({"manifest_path": str(p), "disks": disks})
    return result

@server.resource("diskforge://docs/{page}", mime_type="text/markdown",
                 description=f"DiskForge documentation. Pages: {', '.join(DOCS)}")
def docs(page: str) -> str:
    if page not in DOCS:
        raise ValueError(f"Unknown page '{page}'. Pages: {', '.join(DOCS)}")
    return (REPO / "docs" / DOCS[page]).read_text()

if __name__ == "__main__":
    server.run()
