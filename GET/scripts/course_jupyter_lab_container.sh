#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"

export GET_JUPYTER_PORT="${GET_JUPYTER_PORT:-8888}"
export GET_JUPYTER_IP="${GET_JUPYTER_IP:-127.0.0.1}"
export GET_JUPYTER_DIR="${GET_JUPYTER_DIR:-$HOME}"

if [[ -z "${GET_JUPYTER_TOKEN:-}" ]]; then
  GET_JUPYTER_TOKEN="$(course_apptainer python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
fi
export GET_JUPYTER_TOKEN

echo "[course] starting Jupyter Lab inside the GET container"
echo "[course] repo:         $GET_REPO"
echo "[course] data:         $GET_COURSE_DATA"
echo "[course] work:         $GET_COURSE_WORK"
echo "[course] notebook dir: $GET_JUPYTER_DIR"
echo "[course] bind address: $GET_JUPYTER_IP:$GET_JUPYTER_PORT"
echo
echo "For Cursor or SSH access, open a tunnel in another terminal first:"
echo "  ssh -L $GET_JUPYTER_PORT:127.0.0.1:$GET_JUPYTER_PORT <user>@<teaching-server>"
echo "Then open:"
echo "  http://127.0.0.1:$GET_JUPYTER_PORT/lab?token=$GET_JUPYTER_TOKEN"
if [[ -n "${JUPYTERHUB_SERVICE_PREFIX:-}" ]]; then
  hub_proxy_path="${JUPYTERHUB_SERVICE_PREFIX%/}/proxy/$GET_JUPYTER_PORT/lab?token=$GET_JUPYTER_TOKEN"
  echo
  echo "JupyterHub detected. In the existing JupyterHub browser tab, open this path:"
  echo "  $hub_proxy_path"
  echo "If that gives a 404, the Hub needs jupyter-server-proxy enabled."
fi
echo
echo "Stop the server with Ctrl-C."
echo

course_apptainer bash -lc "PYTHONNOUSERSITE=1 python3 -m jupyter lab --version >/dev/null"

course_apptainer bash -lc "
  cd \"$GET_REPO\" &&
  PYTHONNOUSERSITE=1 python3 -m jupyter lab \
    --no-browser \
    --ip=\"$GET_JUPYTER_IP\" \
    --port=\"$GET_JUPYTER_PORT\" \
    --notebook-dir=\"$GET_JUPYTER_DIR\" \
    --IdentityProvider.token=\"$GET_JUPYTER_TOKEN\" \
    --ServerApp.trust_xheaders=True \
    --ServerApp.allow_remote_access=True
"
