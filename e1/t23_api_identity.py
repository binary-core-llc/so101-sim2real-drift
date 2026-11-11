#!/usr/bin/env python3
"""T23 (D_software): one-image call to the Cosmos-Reason2-8B API (build.nvidia.com, OpenAI-compatible); records the
model ID the server returns, with the date, latency and token counts.

    python3 -I e1/t23_api_identity.py [--image results/c1/nominal_front_rgb.png]
The key is read from ~/.config/gtc/nvidia_api_key (mode 600, saved with hidden input). It is sent only in
the Authorization header and never printed, logged or written. The model name requested comes from the API's own
public model list (GET /v1/models, Nov 6: nvidia/cosmos-reason2-8b); --model for another one (Nov 6:
nvidia/cosmos3-nano-reasoner, from its build.nvidia.com page, as it is not in that list). The image is the C1 sim render (no real photo).
Writes results/e1/t23_<utc>.json. Exit 0 if the call returns a model ID, 1 otherwise.
"""
import argparse
import base64
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GTC = Path(__file__).resolve().parents[1]
URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/cosmos-reason2-8b"
KEY = Path.home() / ".config" / "gtc" / "nvidia_api_key"
PROMPT = "Describe this image in one sentence."


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=str(GTC / "results" / "c1" / "nominal_front_rgb.png"))
    ap.add_argument("--model", default=MODEL)
    a = ap.parse_args(argv)
    if not KEY.exists() or (KEY.stat().st_mode & 0o077):
        print(f"STOP: {KEY} missing or readable by others", file=sys.stderr)
        return 1
    img = Path(a.image)
    body = {"model": a.model, "max_tokens": 128, "temperature": 0.0,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(img.read_bytes()).decode()}}]}]}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json",
                                          "Authorization": "Bearer " + KEY.read_text().strip()})
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "test": "T23", "url": URL,
           "model_requested": a.model, "image": str(img.relative_to(GTC)) if img.is_relative_to(GTC) else str(img),
           "prompt": PROMPT, "max_tokens": 128, "temperature": 0.0}
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp, rec["http_status"] = json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["error"] = re.sub(r"account '[^']*'", "account '<redacted>'", e.read().decode(errors="replace")[:500])
        resp = None
    except (urllib.error.URLError, TimeoutError) as e:
        rec["error"], resp = f"{type(e).__name__}: {e}", None
    rec["latency_s"] = round(time.time() - t0, 2)
    if resp:
        rec["model_returned"] = resp.get("model")
        rec["response_id"] = resp.get("id")
        rec["usage"] = resp.get("usage")
        rec["text"] = (resp.get("choices") or [{}])[0].get("message", {}).get("content")
    out = GTC / "results" / "e1" / f"t23_{rec['utc'].replace(':', '')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1))
    ok = bool(rec.get("model_returned"))
    print(f"T23 {'PASS' if ok else 'FAIL'}: http {rec.get('http_status')}, model returned {rec.get('model_returned')!r}, "
          f"{rec['latency_s']} s -> {out.relative_to(GTC)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
