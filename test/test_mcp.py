"""End-to-end checks for the DiskForge MCP server, driven through a real stdio MCP client.

Run from the repo root with the MCP virtualenv:  mcp_server/.venv/bin/python test/test_mcp.py
Needs the diskforge Docker image built from this checkout (for the --validate flag).
"""
import asyncio, json, shutil, sys
from pathlib import Path
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "output" / "mcp_test"
WATERMARK_CANARY = "6f1c2a9e-4b7d-4e3a-9c58-2d0e8b71f4a3"
PASS = FAIL = 0

def check(desc, ok, detail=""):
    global PASS, FAIL
    PASS, FAIL = PASS + bool(ok), FAIL + (not ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {desc}" + ("" if ok else f"\n         {detail}"))

async def call(session, tool, **args):
    r = await session.call_tool(tool, args, read_timeout_seconds=1800)
    if r.is_error:
        return {"ok": False, "error": r.content[0].text}
    sc = r.structured_content
    if sc is None:
        texts = [json.loads(c.text) for c in r.content]
        return texts[0] if len(texts) == 1 and isinstance(texts[0], dict) else texts
    return sc.get("result", sc) if isinstance(sc, dict) else sc

async def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    params = StdioServerParameters(command=sys.executable, args=[str(REPO / "mcp_server" / "server.py")])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = {t.name: t for t in (await session.list_tools()).tools}
        check("Exposes exactly the four building tools",
              set(tools) == {"validate_manifest", "build", "list_templates", "list_examples"}, sorted(tools))
        check("build is marked destructive, validate read-only",
              tools["build"].annotations.destructive_hint and tools["validate_manifest"].annotations.read_only_hint)

        r = await call(session, "validate_manifest", manifest_path="examples/example_gpt/manifest.json")
        check("Valid example manifest passes", r.get("ok"), r)

        bad = OUT / "bad.json"
        bad.write_text(json.dumps({"disks": [{"name": "x", "type": "APM", "size": "10M", "partitions": []}]}))
        r = await call(session, "validate_manifest", manifest_path=str(bad))
        check("Invalid disk type is rejected with DiskForge's message",
              not r.get("ok") and "Invalid disk type 'APM'" in r.get("output", ""), r)

        r = await call(session, "build", manifest_path="examples/missing/manifest.json")
        check("Missing manifest fails before Docker runs", not r.get("ok") and "not found" in r.get("error", ""), r)

        # A build wipes every .img in /output, so foreign images must stop it
        manifest = OUT / "manifest.json"
        shutil.copy(REPO / "examples/example_watermark/manifest.json", manifest)
        keep = OUT / "students_final.img"
        keep.write_bytes(b"do not delete")
        r = await call(session, "build", manifest_path=str(manifest))
        check("Build refuses when output_dir holds other images", not r.get("ok") and "students_final.img" in r.get("error", ""), r)
        check("The other image is untouched", keep.read_bytes() == b"do not delete")
        keep.unlink()

        r = await call(session, "build", manifest_path=str(manifest))
        check("Watermark example builds", r.get("ok"), r.get("log_tail", r))
        names = sorted(Path(i["path"]).name for i in r.get("images", []))
        check("Both images reported with sizes",
              names == ["training_watermark.img", "training_watermark_mbr.img"]
              and all(i["bytes"] == 128 * 1024 * 1024 for i in r.get("images", [])), r.get("images"))
        check("Fixed canary GUID returned from the build log",
              r.get("canaries", {}).get("training_watermark") == WATERMARK_CANARY, r.get("canaries"))
        check("Generated canary GUID returned for the MBR disk",
              len(r.get("canaries", {}).get("training_watermark_mbr", "")) == 36, r.get("canaries"))

        templates = {t["name"] for t in await call(session, "list_templates")}
        check("Templates listed from templates/", {"linux", "windows10"} <= templates, templates)
        examples = {Path(e["manifest_path"]).parent.name: e for e in await call(session, "list_examples")}
        wm = examples.get("example_watermark", {}).get("disks", [{}])[0].get("features", [])
        cm = examples.get("example_countermeasures", {}).get("disks", [{}])[0].get("features", [])
        check("Examples report disk and partition features", "watermark" in wm and "countermeasure" in cm, (wm, cm))

        doc = await session.read_resource("diskforge://docs/watermark")
        check("Docs resource serves the watermark page", "AI Analysis Watermark" in doc.contents[0].text)
        try:
            await session.read_resource("diskforge://docs/secrets")
            check("Unknown docs page is rejected", False, "read succeeded")
        except Exception:
            check("Unknown docs page is rejected", True)

    shutil.rmtree(OUT, ignore_errors=True)
    print(f"\n  Total: {PASS + FAIL}  Passed: {PASS}  Failed: {FAIL}")
    sys.exit(1 if FAIL else 0)

asyncio.run(main())
