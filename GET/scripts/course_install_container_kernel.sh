#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"

KERNEL_NAME="${GET_KERNEL_NAME:-get-container}"
KERNEL_DISPLAY_NAME="${GET_KERNEL_DISPLAY_NAME:-GET container (course)}"
KERNEL_DIR="${GET_KERNEL_DIR:-$HOME/.local/share/jupyter/kernels/$KERNEL_NAME}"
KERNEL_LAUNCHER="$KERNEL_DIR/kernel.sh"
KERNEL_JSON="$KERNEL_DIR/kernel.json"

mkdir -p "$KERNEL_DIR"

cat > "$KERNEL_LAUNCHER" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

: "${GET_REPO:?GET_REPO is required}"
source "$GET_REPO/scripts/course_env.sh"

exec apptainer exec --nv \
  -B "$HOME:$HOME" \
  "${COURSE_BIND_ARGS[@]}" \
  "$GET_SIF" \
  python3 -m ipykernel_launcher "$@"
EOF

chmod +x "$KERNEL_LAUNCHER"

python3 - "$KERNEL_JSON" "$KERNEL_LAUNCHER" "$KERNEL_DISPLAY_NAME" <<'PY'
import json
import os
import sys

kernel_json, launcher, display_name = sys.argv[1:4]
spec = {
    "argv": [launcher, "-f", "{connection_file}"],
    "display_name": display_name,
    "language": "python",
    "env": {
        "GET_REPO": os.environ["GET_REPO"],
        "GET_COURSE_DATA": os.environ["GET_COURSE_DATA"],
        "GET_COURSE_WORK": os.environ["GET_COURSE_WORK"],
        "GET_SIF": os.environ["GET_SIF"],
        "GET_RSCRIPT": os.environ["GET_RSCRIPT"],
        "GET_MULTIOME_RDS": os.environ["GET_MULTIOME_RDS"],
        "GET_MOTIF_BED": os.environ["GET_MOTIF_BED"],
        "GET_MOTIF_BED_INDEX": os.environ["GET_MOTIF_BED_INDEX"],
        "GET_PRETRAINED_CKPT": os.environ["GET_PRETRAINED_CKPT"],
        "GET_MULTIOME_ZARR": os.environ["GET_MULTIOME_ZARR"],
        "GET_LORA_CKPT": os.environ["GET_LORA_CKPT"],
        "PYTHONNOUSERSITE": "1",
        "HYDRA_FULL_ERROR": "1",
    },
}
with open(kernel_json, "w", encoding="utf-8") as handle:
    json.dump(spec, handle, indent=2)
    handle.write("\\n")
PY

echo "[ok] installed Jupyter kernel:"
echo "  $KERNEL_DISPLAY_NAME"
echo "  $KERNEL_DIR"
echo
echo "Refresh the JupyterHub launcher and choose '$KERNEL_DISPLAY_NAME'."
