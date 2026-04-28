#!/bin/bash
# run_benchmark_with_ollama.sh
# Installs ollama if needed, pulls the Qiskit model, runs benchmark_v3.py,
# and shuts everything down cleanly.
#
# Usage (local):
#   ./run_benchmark_with_ollama.sh
#   ./run_benchmark_with_ollama.sh --repair-template
#   ./run_benchmark_with_ollama.sh --multi-turn
#   ./run_benchmark_with_ollama.sh --resume
#   ./run_benchmark_with_ollama.sh --resume-from run_v3_20260427_194907/benchmark_qhe_v3_20260427_194907.json
#
# LSF example (bluevela):
#   bsub -n 1 -G grp_preemptable -q preemptable \
#     -gpu "num=1/task:mode=shared:j_exclusive=yes" \
#     "cd /proj/dmfexp/eiger/users/ajbozarth/toolbox/mellea/qiskit_code_validation/benchmarking && \
#      bash run_benchmark_with_ollama.sh"

set -euo pipefail

# --- Helper functions ---
log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# --- Paths ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MELLEA_EXAMPLE_DIR="${MELLEA_EXAMPLE_DIR:-/proj/dmfexp/eiger/users/ajbozarth/mellea/docs/examples/instruct_validate_repair/qiskit_code_validation}"

# --- Ollama configuration ---
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
if [[ -n "${CACHE_DIR:-}" ]]; then
    OLLAMA_DIR="${CACHE_DIR}/ollama"
else
    log "WARNING: CACHE_DIR not set. Ollama models will download to ~/.ollama (default)"
    OLLAMA_DIR="$HOME/.ollama"
fi
OLLAMA_BIN="${OLLAMA_BIN:-$(command -v ollama 2>/dev/null || echo "$HOME/.local/bin/ollama")}"

# The Qiskit-specialized model (~14GB — download only happens once if CACHE_DIR is set)
OLLAMA_MODEL="hf.co/Qiskit/mistral-small-3.2-24b-qiskit-GGUF:latest"

# Log directory
LOGDIR="${SCRIPT_DIR}/logs/$(date +%Y-%m-%d-%H:%M:%S)"
mkdir -p "$LOGDIR"
log "Log directory: $LOGDIR"

# --- Cleanup ---
cleanup() {
    if [[ "${OLLAMA_EXTERNAL:-0}" == "1" ]]; then
        log "Ollama managed externally (OLLAMA_EXTERNAL=1) — skipping shutdown"
        return
    fi
    log "Shutting down ollama server..."
    if [[ -n "${OLLAMA_PID:-}" ]] && kill -0 "$OLLAMA_PID" 2>/dev/null; then
        kill "$OLLAMA_PID" 2>/dev/null
        wait "$OLLAMA_PID" 2>/dev/null || true
    fi
    log "Ollama stopped."
}
trap cleanup EXIT

# --- Install ollama binary if missing ---
if [[ ! -x "$OLLAMA_BIN" ]]; then
    log "Ollama binary not found at $OLLAMA_BIN — downloading latest release..."
    OLLAMA_INSTALL_DIR="$(dirname "$OLLAMA_BIN")"
    mkdir -p "$OLLAMA_INSTALL_DIR"

    OLLAMA_VERSION=$(curl -fsSL https://api.github.com/repos/ollama/ollama/releases/latest \
        | grep '"tag_name"' | head -1 | cut -d'"' -f4)
    log "Latest ollama version: $OLLAMA_VERSION"

    DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst"
    log "Downloading from $DOWNLOAD_URL (includes CUDA libs, ~1.9GB)..."

    OLLAMA_PREFIX="$(dirname "$OLLAMA_INSTALL_DIR")"
    curl -fsSL "$DOWNLOAD_URL" | tar --use-compress-program=unzstd -x -C "$OLLAMA_PREFIX"
    chmod +x "$OLLAMA_BIN"
    log "Installed ollama $OLLAMA_VERSION to $OLLAMA_PREFIX"
fi

# --- Check if ollama is already running ---
if curl -sf "http://${OLLAMA_HOST}:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
    log "Ollama already running on ${OLLAMA_HOST}:${OLLAMA_PORT} — using existing server"
    OLLAMA_PID=""
else
    # Find a free port
    while ss -tln 2>/dev/null | grep -q ":${OLLAMA_PORT} " || \
          netstat -tln 2>/dev/null | grep -q ":${OLLAMA_PORT} "; do
        log "Port $OLLAMA_PORT in use, trying $((OLLAMA_PORT + 1))..."
        OLLAMA_PORT=$((OLLAMA_PORT + 1))
    done

    log "Starting ollama server on ${OLLAMA_HOST}:${OLLAMA_PORT}..."
    export OLLAMA_HOST="${OLLAMA_HOST}:${OLLAMA_PORT}"
    export OLLAMA_MODELS_DIR="${OLLAMA_DIR}/models"
    mkdir -p "$OLLAMA_MODELS_DIR"

    if [[ -d "/usr/local/cuda" ]]; then
        export LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:${LD_LIBRARY_PATH:-}"
        log "Added system CUDA to LD_LIBRARY_PATH"
    fi

    "$OLLAMA_BIN" serve > "$LOGDIR/ollama.log" 2>&1 &
    OLLAMA_PID=$!
    log "Ollama server PID: $OLLAMA_PID"

    log "Waiting for ollama to be ready..."
    for i in $(seq 1 120); do
        if curl -sf "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
            log "Ollama ready after ${i}s"
            break
        fi
        if ! kill -0 "$OLLAMA_PID" 2>/dev/null; then
            die "Ollama process died during startup. Check $LOGDIR/ollama.log"
        fi
        sleep 1
    done

    if ! curl -sf "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
        die "Ollama failed to start within 120s. Check $LOGDIR/ollama.log"
    fi
fi

# --- Pull the Qiskit model ---
export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
if "$OLLAMA_BIN" list 2>/dev/null | grep -q "^${OLLAMA_MODEL}"; then
    log "Model $OLLAMA_MODEL already pulled"
else
    log "Pulling $OLLAMA_MODEL (~14GB, this will take a while)..."
    "$OLLAMA_BIN" pull "$OLLAMA_MODEL" 2>&1 | tail -1
fi

# --- Warm up the model ---
if [[ "${OLLAMA_SKIP_WARMUP:-0}" == "1" ]]; then
    log "Skipping model warmup (OLLAMA_SKIP_WARMUP=1)"
else
    log "Warming up $OLLAMA_MODEL (first load into GPU memory is slow)..."
    curl -sf "http://127.0.0.1:${OLLAMA_PORT}/api/generate" \
        -d "{\"model\": \"${OLLAMA_MODEL}\", \"prompt\": \"hi\", \"stream\": false}" \
        -o /dev/null --max-time 300 \
        || log "Warning: warmup timed out (will load on first benchmark run)"
    log "Warmup complete."
fi

# --- Run the benchmark ---
log "Starting benchmark..."
log "Example dir: $MELLEA_EXAMPLE_DIR"
log "Benchmark args: ${*:-<none> (running both phases)}"

uv run --quiet "$SCRIPT_DIR/benchmark_v3.py" \
    --example-dir "$MELLEA_EXAMPLE_DIR" \
    "$@" \
    2>&1 | tee "$LOGDIR/benchmark.log"

EXIT_CODE=${PIPESTATUS[0]}
log "Benchmark finished with exit code: $EXIT_CODE"
log "Full log: $LOGDIR/benchmark.log"
exit $EXIT_CODE
