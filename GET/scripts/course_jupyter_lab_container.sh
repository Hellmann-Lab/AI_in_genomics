#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"

export GET_JUPYTER_PORT="${GET_JUPYTER_PORT:-8888}"
export GET_JUPYTER_IP="${GET_JUPYTER_IP:-127.0.0.1}"
export GET_JUPYTER_DIR="${GET_JUPYTER_DIR:-$HOME}"

echo "[course] starting Jupyter Lab inside the GET container"
echo "[course] repo:         $GET_REPO"
echo "[course] data:         $GET_COURSE_DATA"
echo "[course] work:         $GET_COURSE_WORK"
echo "[course] notebook dir: $GET_JUPYTER_DIR"
echo "[course] bind address: $GET_JUPYTER_IP:$GET_JUPYTER_PORT"
echo
echo "If you connect from your laptop by SSH, open a tunnel in another terminal first:"
echo "  ssh -L $GET_JUPYTER_PORT:127.0.0.1:$GET_JUPYTER_PORT <user>@<teaching-server>"
echo
echo "Then open the URL printed by Jupyter Lab. Stop the server with Ctrl-C."
echo

course_apptainer bash -lc "PYTHONNOUSERSITE=1 python3 -m jupyter lab --version >/dev/null"

course_apptainer bash -lc "
  cd \"$GET_REPO\" &&
  PYTHONNOUSERSITE=1 python3 -m jupyter lab \
    --no-browser \
    --ip=\"$GET_JUPYTER_IP\" \
    --port=\"$GET_JUPYTER_PORT\" \
    --notebook-dir=\"$GET_JUPYTER_DIR\"
"
