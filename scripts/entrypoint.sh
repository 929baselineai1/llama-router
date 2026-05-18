#!/bin/bash
# Llama Router entrypoint
# Starts llama-server + UI backend

set -e

PORTS=${PORTS:-"8080 8090 8099"}
MODEL_DIR=${MODEL_DIR:-"/models"}
PRESETS=${PRESETS:-"${MODEL_DIR}/llama-presets.ini"}
NGPU_LAYERS=${NGPU_LAYERS:-99}
CTX_SIZE=${CTX_SIZE:-131072}
BATCH_SIZE=${BATCH_SIZE:-512}
MODEL=${MODEL:-""}

echo "[llama-router] Starting..."
echo "[llama-router] Model dir: ${MODEL_DIR}"
echo "[llama-router] Presets: ${PRESETS}"

# Start llama-server in background
SERVER_CMD="llama-server"
SERVER_CMD+=" --models-dir ${MODEL_DIR}"
SERVER_CMD+=" --host 0.0.0.0 --port 8080"
SERVER_CMD+=" -c ${CTX_SIZE} -ngl ${NGPU_LAYERS}"
SERVER_CMD+=" -b ${BATCH_SIZE} -ub ${BATCH_SIZE}"
SERVER_CMD+=" --flash-attn on"
SERVER_CMD+=" --models-preset ${PRESETS}"

if [ -n "$MODEL" ]; then
    SERVER_CMD+=" --model ${MODEL}"
fi

echo "[llama-router] Starting llama-server..."
echo "[llama-router] CMD: ${SERVER_CMD}"
${SERVER_CMD} > /tmp/llama-server.log 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > /tmp/llama-server.pid
echo "[llama-router] llama-server PID: ${SERVER_PID}"

# Wait for server to be ready
echo "[llama-router] Waiting for server..."
for i in $(seq 1 30); do
    if curl -s --max-time 2 http://127.0.0.1:8080/props > /dev/null 2>&1; then
        echo "[llama-router] Server ready after ${i}s"
        break
    fi
    sleep 1
done

# Start UI backend (saver)
echo "[llama-router] Starting UI backend on port 8090..."
cd /app/ui
python3 llama-saver.py > /tmp/saver.log 2>&1 &
SAVER_PID=$!
echo "[llama-router] Saver PID: ${SAVER_PID}"

# Start HTTP server for UI on port 8099
echo "[llama-router] Starting UI server on port 8099..."
python3 -m http.server 8099 --bind 0.0.0.0 --directory /app/ui > /tmp/ui-server.log 2>&1 &
UI_PID=$!
echo "[llama-router] UI server PID: ${UI_PID}"

echo "[llama-router] All services started"
echo "[llama-router] UI: http://localhost:8099/routerUI.html"
echo "[llama-router] API: http://localhost:8090"

# Keep container alive
wait