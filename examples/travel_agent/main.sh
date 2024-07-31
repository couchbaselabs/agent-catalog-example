#!/bin/bash

# Load all of our environment variables.
source .env

# TODO (GLENN): We need to actually wait for the server to appear
# Start our agent server.
fastapi run my_servers/agent_server.py --port "${AGENT_CONN_PORT}" &
AGENT_SERVER_PID=$!
sleep 1
echo "==="
echo "Agent server is running with PID $AGENT_SERVER_PID."
echo "==="
sleep 4

# Start our rewards server.
fastapi run my_servers/rewards_server.py --port "${REWARDS_CONN_PORT}" &
REWARDS_SERVER_PID=$!
sleep 1
echo "==="
echo "Rewards server is running with PID $REWARDS_SERVER_PID."
echo "==="
sleep 4

# Start our Streamlit app.
streamlit run app.py
