#!/usr/bin/env python3
"""T32: write wrapper layers that point the course USDs at the local asset mirror.

    .venv/bin/python -I tools/make_local_wrappers.py

For each course USD with remote references, assets/local/<name>.local.usda:
  - sublayers the UNMODIFIED course file (container path), keeps its defaultPrim/upAxis/mpu;
  - overrides, at the same spec paths, every remote asset-valued attribute (e.g. the MDL
    `info:mdl:sourceAsset`) and every remote payload/reference, with the mirrored copy.
A stronger layer's explicit list op replaces the weaker one, so the S3 payload is never opened.
Our scripts load these wrappers via env-cfg spawn.usd_path overrides (sim/local_assets.py).
"""
import json
import sys
import urllib.parse
from pathlib import Path

from pxr import Sdf

HOME = Path.home()
COURSE_HOST = HOME / "gtc2027/Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd"
COURSE_CTR = "/workspace/Sim-to-Real-SO-101-Workshop/source/sim_to_real_so101/assets/usd"
MIRROR_CTR = "/workspace/assets_mirror"
OUT = Path(__file__).resolve().parents[1] / "assets" / "local"
FILES = ["lightbox-simple.usd", "mat.usda", "SO-ARM101-USD.usd", "Vial_opaque.usda"]


def mirrored(url):
    u = urllib.parse.urlparse(url)
    return f"{MIRROR_CTR}/{u.netloc}/{urllib.parse.unquote(u.path.lstrip('/'))}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in FILES:
        src = Sdf.Layer.FindOrOpen(str(COURSE_HOST / name))
        w = Sdf.Layer.CreateAnonymous(".usda")
        w.subLayerPaths.append(f"{COURSE_CTR}/{name}")
        if src.defaultPrim:
            w.defaultPrim = src.defaultPrim
        for key in ("upAxis", "metersPerUnit"):
            if src.pseudoRoot.HasInfo(key):
                w.pseudoRoot.SetInfo(key, src.pseudoRoot.GetInfo(key))
        changes = []

        def visit(path):
            spec = src.GetObjectAtPath(path)
            if isinstance(spec, Sdf.AttributeSpec) and spec.HasInfo("default"):
                v = spec.default
                if isinstance(v, Sdf.AssetPath) and "://" in v.path:
                    owner = Sdf.CreatePrimInLayer(w, path.GetPrimPath())
                    a = Sdf.AttributeSpec(owner, path.name, spec.typeName, spec.variability)
                    a.default = Sdf.AssetPath(mirrored(v.path))
                    changes.append({"attr": str(path), "from": v.path, "to": a.default.path})
            elif isinstance(spec, Sdf.PrimSpec):
                for kind in ("payloadList", "referenceList"):
                    lst = getattr(spec, kind)
                    items = list(lst.GetAddedOrExplicitItems()) if hasattr(lst, "GetAddedOrExplicitItems") else (
                        list(lst.prependedItems) + list(lst.appendedItems) + list(lst.explicitItems))
                    if any("://" in it.assetPath for it in items):
                        owner = Sdf.CreatePrimInLayer(w, path)
                        new = []
                        for it in items:
                            ap = mirrored(it.assetPath) if "://" in it.assetPath else it.assetPath
                            new.append(Sdf.Payload(ap, it.primPath, it.layerOffset) if kind == "payloadList"
                                       else Sdf.Reference(ap, it.primPath, it.layerOffset))
                        getattr(owner, kind).explicitItems = new
                        changes.append({kind: str(path), "from": [i.assetPath for i in items], "to": [n.assetPath for n in new]})
        src.Traverse(Sdf.Path.absoluteRootPath, visit)
        out = OUT / (Path(name).stem + ".local.usda")
        w.Export(str(out))
        report[name] = {"wrapper": str(out.relative_to(OUT.parents[1])), "changes": changes}
        print(f"{name}: {len(changes)} overrides -> {out.name}")
    (OUT / "wrappers.json").write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
