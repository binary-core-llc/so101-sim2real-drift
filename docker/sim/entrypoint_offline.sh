#!/bin/bash
# Modified by Binary Core LLC, 2026, from the course's docker/sim/entrypoint.sh (ce807d9).
# Binary Core patch: no runtime `pip install -e`, which downloads build dependencies from PyPI at
# every container start (an outage would fail every sweep cell); the course package is imported
# from the mounted source via PYTHONPATH instead.
# Binary Core patch: `|| true` added after `source /root/env`, so a missing or failing env file
# does not end the script silently under `set -e`.
# Everything else is the same as the course entrypoint (see entrypoint_offline.diff).
set -e

ISAAC_SIM=/workspace/isaaclab/_isaac_sim

export CARB_APP_PATH=$ISAAC_SIM/kit
export ISAAC_PATH=$ISAAC_SIM
export EXP_PATH=$ISAAC_SIM/apps
source ${ISAAC_SIM}/setup_python_env.sh
source /root/env 2>/dev/null || true

cat > /usr/local/bin/python << 'WRAPPER'
#!/bin/bash
exec /workspace/isaaclab/_isaac_sim/python.sh "$@"
WRAPPER
chmod +x /usr/local/bin/python

export PYTHONPATH=/workspace/Sim-to-Real-SO-101-Workshop/source${PYTHONPATH:+:$PYTHONPATH}

exec "$@"
