# MCP Server

DiskForge ships an [MCP](https://modelcontextprotocol.io) server so Claude Code, Claude Desktop, or any MCP client can write, validate, and build manifests for you. It runs on the host and starts the `diskforge` Docker image for each call, so the privileged container works the same as with `docker run`.

The server builds images only. It has no tools that inspect built images (`mmls`, `fls`, `strings`), so it can't be used to solve them.

---

## Setup

```bash
# 1. Build the Docker image from this checkout (the server needs its --validate flag)
docker build -t diskforge .

# 2. Create the server's virtualenv
python3 -m venv mcp_server/.venv
mcp_server/.venv/bin/pip install -e mcp_server

# 3. Register it with Claude Code
claude mcp add diskforge -- "$(pwd)/mcp_server/.venv/bin/python" "$(pwd)/mcp_server/server.py"
```

For other clients, use the same command and arguments in the client's server configuration. Set `DISKFORGE_IMAGE` in the server's environment to use an image tag other than `diskforge`.

---

## Tools

| Tool | What it does |
|------|--------------|
| `validate_manifest(manifest_path, files_dir="files")` | Runs DiskForge's validator in the container. Returns `ok` and DiskForge's message. Builds nothing |
| `build(manifest_path, files_dir="files", output_dir="", replace_other_images=false)` | Builds every disk in the manifest. Returns the image paths and sizes, watermark canary GUIDs, and the last 60 log lines |
| `list_templates()` | OS templates for `populate.template` |
| `list_examples()` | Example manifests with each disk's type, size, and features |

Paths are host paths. Relative paths resolve against the DiskForge repo. Inside a manifest, file sources are container paths under `/files`, which is `files_dir` on the host.

!!! warning "Builds delete other images"
    DiskForge removes every `.img` in the output directory before it builds. `output_dir` defaults to the manifest's directory, and `build` refuses to run when that directory holds images the manifest doesn't produce. Pass a different `output_dir`, or set `replace_other_images` to `true` to allow the deletion.

A build takes minutes and has a 30-minute timeout.

## Resources

`diskforge://docs/{page}` serves these documentation pages so a client can write correct manifests: `manifest-reference`, `encryption`, `templates`, `injection`, `countermeasures`, `watermark`.

---

## Testing

```bash
mcp_server/.venv/bin/python test/test_mcp.py
```

Starts the server through a real MCP client over stdio and runs 15 checks: the tool list and its read-only and destructive hints, validation pass and fail, the missing-manifest and other-images refusals, a full build of `example_watermark` (images, sizes, and both canary GUIDs), the list tools, and the docs resource. It needs Docker and the `diskforge` image, and builds into `output/mcp_test/`, which it removes afterward.
