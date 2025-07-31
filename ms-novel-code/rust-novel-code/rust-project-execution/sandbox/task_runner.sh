#!/usr/bin/env bash
set -euo pipefail

IMAGE=rust-notebook-validator
NOTEBOOK="$1"
RUNS="${2:-1}"
TIMEOUT="${3:-120}"

if [[ -z "$NOTEBOOK" ]]; then
  echo "Usage: $0 colab/001.ipynb [runs] [timeout_seconds]"
  exit 1
fi

# Check if image exists
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Docker image '$IMAGE' not found."
  echo "Please run 'setup.sh' if you're on Linux/macOS, or 'setup.ps1' if you're on Windows/VSCode."
  exit 1
fi

# Run the validator inside the container
echo "Validating $NOTEBOOK ($RUNS runs, ${TIMEOUT}s timeout)..."

docker run --rm \
  -v "$(pwd)/colab:/app/colab:ro" \
  -v "$(pwd)/tasks:/tasks" \
  "$IMAGE" \
    "/app/colab/$(basename "$NOTEBOOK")" \
    --runs "$RUNS" \
    --timeout "$TIMEOUT"
