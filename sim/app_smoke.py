# Minimal Isaac Sim start test (headless, cameras on): did the RTX renderer come up?
#   sim/run_sim.sh gtc-smoke python /workspace/gtc/sim/app_smoke.py --headless
import argparse
import os

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
a.enable_cameras = True
app = AppLauncher(a).app
print("APP_STARTED_OK", flush=True)
for _ in range(20):
    app.update()
print("APP_UPDATES_OK", flush=True)
os._exit(0)
