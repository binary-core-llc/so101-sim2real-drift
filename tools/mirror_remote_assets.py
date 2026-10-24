#!/usr/bin/env python3
"""T32: mirror every remote asset the course scene loads, so no run depends on NVIDIA's S3.

    .venv/bin/python -I tools/mirror_remote_assets.py [--mirror ~/sim2real/assets_mirror]

1. Collect the remote URLs referenced by the course USDs (sublayers, references, payloads,
   asset-valued attributes such as info:mdl:sourceAsset).
2. Download each one to <mirror>/<host>/<path>, then follow its own dependencies:
   USD files via UsdUtils.ExtractExternalReferences, MDL files via their `import` lines and
   quoted file names. Relative paths resolve against the file's URL.
3. Inside the mirrored USD files, absolute remote URLs are rewritten to relative paths into the
   mirror (UsdUtils.ModifyAssetPaths), so each mirrored file is self-contained. The untouched
   download is kept next to it as <file>.orig.
4. Write <mirror>/manifest.json: url -> local path, bytes, sha256 (of the original download).
The course files themselves are never modified (see make_local_wrappers.py).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from pxr import Sdf, UsdUtils

COURSE_USD = Path.home() / "gtc2027/Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd"
COURSE_FILES = ["lightbox-simple.usd", "mat.usda", "SO-ARM101-USD.usd", "Vial_opaque.usda",
                "Vial_rack_simple.usda", "Vial.usda", "SO-ARM101-USD-NO-CAMERA.usd", "tray.usda"]
USD_EXT = (".usd", ".usda", ".usdc")
FILE_RE = re.compile(r'"([^"\s]+\.(?:png|jpg|jpeg|exr|hdr|tga|tif|tiff|dds|mdl|ies|usd|usda|usdc))"', re.I)
IMPORT_RE = re.compile(r'^\s*import\s+([^;]+);', re.M)


def is_remote(p):
    return "://" in p


def local_for(url, mirror):
    u = urllib.parse.urlparse(url)
    return mirror / u.netloc / urllib.parse.unquote(u.path.lstrip("/"))


def fetch(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def usd_deps(path):
    sub, refs, pls = UsdUtils.ExtractExternalReferences(str(path))
    return [p for p in sub + refs + pls if p]


def mdl_deps(path):
    txt = path.read_text(errors="replace")
    deps = set(FILE_RE.findall(txt))
    # `import ::a::b::*;` or `import .::x::*;` -> module file paths relative to the search root;
    # only relative (".::" / "..::") imports point next to this file
    for imp in IMPORT_RE.findall(txt):
        imp = imp.strip()
        if imp.startswith(".::") or imp.startswith("..::"):
            parts = [p for p in imp.split("::") if p not in ("*",)]
            mod = "/".join(parts[:-1] if len(parts) > 1 and not parts[-1].endswith("*") else parts)
            deps.add(mod.replace(".::", "./").rstrip("/") + ".mdl")
    return sorted(deps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mirror", default=str(Path.home() / "sim2real/assets_mirror"))
    a = ap.parse_args()
    mirror = Path(a.mirror).expanduser()
    mirror.mkdir(parents=True, exist_ok=True)

    queue, seen, manifest, skipped = [], set(), {}, []
    for f in COURSE_FILES:
        for d in usd_deps(COURSE_USD / f):
            if is_remote(d):
                queue.append((d, f"course:{f}"))
    while queue:
        url, parent = queue.pop()
        if url in seen:
            continue
        seen.add(url)
        dest = local_for(url, mirror)
        try:
            fetch(url, dest)
        except Exception as e:  # a referenced file that does not exist upstream
            skipped.append({"url": url, "parent": parent, "error": str(e)})
            continue
        data = dest.read_bytes()
        manifest[url] = {"local": str(dest.relative_to(mirror)), "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(), "referenced_by": parent}
        deps = []
        if dest.suffix.lower() in USD_EXT:
            deps = usd_deps(dest)
        elif dest.suffix.lower() == ".mdl":
            deps = mdl_deps(dest)
        for d in deps:
            if d.startswith("::") or d in ("OmniPBR.mdl", "OmniSurface.mdl", "OmniGlass.mdl"):
                continue  # Kit's built-in MDL library
            full = d if is_remote(d) else urllib.parse.urljoin(url, d)
            if is_remote(full):
                queue.append((full, url))
        print(f"got {len(data):>10} B  {url}")

    # make mirrored USD files self-contained: absolute remote URLs -> relative paths in the mirror
    rewritten = []
    for url, m in manifest.items():
        p = mirror / m["local"]
        if p.suffix.lower() not in USD_EXT:
            continue
        lyr = Sdf.Layer.FindOrOpen(str(p))
        changed = []

        def fix(ap_, p=p, changed=changed):
            if is_remote(ap_):
                tgt = local_for(ap_, mirror)
                rel = os.path.relpath(tgt, p.parent)
                changed.append((ap_, rel))
                return rel
            return ap_
        UsdUtils.ModifyAssetPaths(lyr, fix)
        if changed:
            shutil.copy2(p, str(p) + ".orig")
            lyr.Save()
            rewritten.append({"file": m["local"], "changes": changed})

    out = {"mirror": str(mirror), "files": manifest, "skipped": skipped, "rewritten_usd": rewritten}
    (mirror / "manifest.json").write_text(json.dumps(out, indent=1))
    print(f"{len(manifest)} files mirrored, {len(skipped)} not found upstream, {len(rewritten)} USD files rewritten")
    for s in skipped:
        print("  missing:", s["url"], "(from", s["parent"] + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
