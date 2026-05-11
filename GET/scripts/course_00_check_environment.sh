#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

echo "[course] repo:          $GET_REPO"
echo "[course] data:          $GET_COURSE_DATA"
echo "[course] work:          $GET_COURSE_WORK"
echo "[course] apptainer sif: $GET_SIF"
echo "[course] host Rscript:  $GET_RSCRIPT"
echo

missing=0
command -v apptainer >/dev/null 2>&1 || { echo "[missing] apptainer command" >&2; missing=1; }
[[ -x "$GET_RSCRIPT" ]] || { echo "[missing] executable Rscript: $GET_RSCRIPT" >&2; missing=1; }
course_require_file "$GET_MULTIOME_RDS" "multiome1 Seurat RDS" || missing=1
course_require_file "$GET_MOTIF_BED" "motif BED" || missing=1
course_require_file "$GET_PRETRAINED_CKPT" "pretrained checkpoint" || missing=1

if [[ ! -e "$GET_SIF" ]]; then
  echo "[missing] Apptainer image: $GET_SIF" >&2
  echo "Create it with:" >&2
  echo "  mkdir -p \"$(dirname "$GET_SIF")\"" >&2
  echo "  apptainer pull \"$GET_SIF\" docker://fuxialexander/get_model:latest" >&2
  missing=1
fi

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

course_apptainer bash -lc 'PYTHONNOUSERSITE=1 python3 - <<PY
import torch, zarr
print("[container] torch", torch.__version__, "cuda_available", torch.cuda.is_available())
print("[container] zarr", zarr.__version__)
PY'

echo "[ok] environment checks passed"
