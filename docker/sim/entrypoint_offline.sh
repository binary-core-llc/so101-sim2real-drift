#!/bin/bash
# GTC copy of the course docker/sim/entrypoint.sh without the runtime `pip install -e`, which
# downloads build dependencies from PyPI at every container start (an outage would fail every
# sweep cell). The course package is imported from the mounted source via PYTHONPATH instead.
# Everything else is the same as the course entrypoint.
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
