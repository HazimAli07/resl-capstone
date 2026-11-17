#!/bin/zsh
set -e
demo_project_dir="${0:A:h}"
cd -- "$demo_project_dir"
demo_python="$demo_project_dir/.venv/bin/python"
if [[ ! -x "$demo_python" ]]; then
  demo_python="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
fi
if [[ ! -x "$demo_python" ]]; then
  demo_python="$(command -v python3)"
fi
echo "Starting RESL at http://localhost:8501"
echo "Keep this Terminal window open. Press Ctrl+C to stop."
exec "$demo_python" -m resl.mini_demo --port 8501 --open-browser
