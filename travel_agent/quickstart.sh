#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")" || exit

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 [controlflow]"
    exit 1
fi

trap on_ctrl_c INT
function on_ctrl_c() {
    echo "Ctrl-C issued, killing spawned processes."
    kill "$(ps -ef | grep -E 'agent_server.py|prefect|rewards_server.py|uvicorn' | grep -v 'grep' | awk '{print $2}')"
}

if [ "$1" == "controlflow" ]; then
  echo "Spawning new Prefect server."
  export PREFECT_API_URL="http://127.0.0.1:4200/api"
  prefect server start &
  echo "Starting agent server."
  fastapi run src/endpoints/agent_server.py --port 10000 &

else
  echo "Invalid argument. Usage: $0 [controlflow]"
  exit 1
fi

echo "Starting (dummy) rewards server."
fastapi run src/endpoints/rewards_server.py --port 10001 &

echo "Starting UI."
streamlit run src/app.py
