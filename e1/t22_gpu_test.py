#!/usr/bin/env python3
"""T22 (D_software): Cosmos-Reason2-2B on the A4500, one image, then one image pair (E1 sends two labelled images),
with GPU memory and latency. Sim render only (no real photo, no E1 result).

    .venv-e1/bin/python -I e1/t22_gpu_test.py           # with the GR00T server stopped
Model card (README at revision 9ce19a19): Qwen3VLForConditionalGeneration, attn_implementation "sdpa", the
<think>/<answer> format, max_new_tokens 4096 "to avoid truncated response", and "a minimum of 24 GB of GPU memory"
(tested in BF16 on H100/A100); loaded here in BF16. Generation settings are the checkpoint's generation_config
(sampling), seeded. GPU memory: torch peak allocated/reserved per case, plus nvidia-smi sampled every 0.25 s
(whole GPU, other processes included). Writes results/e1/t22_<utc>.json.
"""
import datetime as dt
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import torch
import transformers
from PIL import Image

GTC = Path(__file__).resolve().parents[1]
MODEL = Path.home() / "sim2real" / "models" / "nvidia" / "Cosmos-Reason2-2B"
REVISION = "9ce19a195e423419c349abfc86fd07178b230561"
IMAGE = GTC / "results" / "c1" / "nominal_front_rgb.png"
FORMAT = ("Answer the question in the following format: <think>\nyour reasoning\n</think>\n\n<answer>\nyour answer\n"
          "</answer>.")
MAX_NEW = 4096


class SmiSampler:
    def __init__(self, every=0.25):
        self.every, self.peak, self.stop = every, 0, threading.Event()
        self.t = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True).stdout.strip()
            if out:
                self.peak = max(self.peak, int(out.splitlines()[0]))
            time.sleep(self.every)


def smi_used():
    return int(subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                              capture_output=True, text=True).stdout.split()[0])


def run_case(model, processor, images, question):
    content = [{"type": "image", "image": im} for im in images] + [{"type": "text", "text": question}]
    msgs = [{"role": "system", "content": [{"type": "text", "text": FORMAT}]}, {"role": "user", "content": content}]
    inputs = processor.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, return_dict=True,
                                           return_tensors="pt").to(model.device)
    torch.cuda.reset_peak_memory_stats()
    torch.manual_seed(0)
    torch.cuda.synchronize()
    t0 = time.time()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW)
    torch.cuda.synchronize()
    dt_s = time.time() - t0
    new = out[0, inputs["input_ids"].shape[1]:]
    return {"n_images": len(images), "input_tokens": int(inputs["input_ids"].shape[1]), "output_tokens": int(new.numel()),
            "seconds": round(dt_s, 2), "tokens_per_s": round(new.numel() / dt_s, 1),
            "torch_peak_allocated_mib": round(torch.cuda.max_memory_allocated() / 2**20),
            "torch_peak_reserved_mib": round(torch.cuda.max_memory_reserved() / 2**20),
            "text": processor.decode(new, skip_special_tokens=True)}


def main():
    rec = {"utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "test": "T22", "model": str(MODEL),
           "revision": REVISION, "dtype": "bfloat16", "attn": "sdpa", "max_new_tokens": MAX_NEW,
           "torch": torch.__version__, "cuda": torch.version.cuda, "transformers": transformers.__version__,
           "gpu": torch.cuda.get_device_name(0), "image": str(IMAGE.relative_to(GTC)),
           "gpu_used_before_mib": smi_used(),
           "compute_apps_before": subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                                                  "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()}
    smi = SmiSampler()
    smi.t.start()
    t0 = time.time()
    model = transformers.Qwen3VLForConditionalGeneration.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda",
                                                                         attn_implementation="sdpa")
    processor = transformers.AutoProcessor.from_pretrained(MODEL)
    torch.cuda.synchronize()
    rec["load_s"] = round(time.time() - t0, 1)
    rec["after_load_allocated_mib"] = round(torch.cuda.memory_allocated() / 2**20)
    rec["after_load_gpu_used_mib"] = smi_used()
    rec["generation_config"] = model.generation_config.to_dict()
    im = Image.open(IMAGE).convert("RGB")
    rec["cases"] = [
        run_case(model, processor, [im], "Describe the scene: which objects are on the table and where is the camera looking?"),
        run_case(model, processor, [im, im], "Image 1 is A (sim reference) and image 2 is B (current photo). Is the camera "
                                             "pose in B different from A? Describe any difference."),
    ]
    smi.stop.set()
    smi.t.join()
    rec["nvidia_smi_peak_used_mib"] = smi.peak
    rec["gpu_total_mib"] = round(torch.cuda.get_device_properties(0).total_memory / 2**20)
    out = GTC / "results" / "e1" / f"t22_{rec['utc'].replace(':', '')}.json"
    out.write_text(json.dumps(rec, indent=1))
    for c in rec["cases"]:
        print(f"{c['n_images']} image(s): {c['input_tokens']} in / {c['output_tokens']} out tokens, {c['seconds']} s, "
              f"torch peak {c['torch_peak_allocated_mib']} MiB allocated / {c['torch_peak_reserved_mib']} reserved")
    print(f"load {rec['load_s']} s; GPU used before {rec['gpu_used_before_mib']} MiB, after load {rec['after_load_gpu_used_mib']}, "
          f"nvidia-smi peak {smi.peak} of {rec['gpu_total_mib']} MiB -> {out.relative_to(GTC)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
