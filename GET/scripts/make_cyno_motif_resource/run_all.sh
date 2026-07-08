#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

: "${GET_CYNO_ANNOT_DIR:?GET_CYNO_ANNOT_DIR is required}"
: "${GET_CYNO_FASTA:?GET_CYNO_FASTA is required}"
: "${GET_CYNO_GTF:?GET_CYNO_GTF is required}"
: "${GET_CYNO_MOTIF_PREFIX:?GET_CYNO_MOTIF_PREFIX is required}"
: "${GET_VIERSTRA_V1_DIR:?GET_VIERSTRA_V1_DIR is required}"
: "${GET_CYNO_WORK_DIR:?GET_CYNO_WORK_DIR is required}"

mkdir -p "$GET_CYNO_ANNOT_DIR" "$GET_VIERSTRA_V1_DIR" "$GET_CYNO_WORK_DIR"

echo "[cyno-motif] repo: $REPO_ROOT"
echo "[cyno-motif] annotation dir: $GET_CYNO_ANNOT_DIR"
echo "[cyno-motif] FASTA: $GET_CYNO_FASTA"
echo "[cyno-motif] GTF: $GET_CYNO_GTF"
if [[ -n "${TEST_REGION:-}" ]]; then
  echo "[cyno-motif] TEST_REGION: $TEST_REGION"
fi

bash "$SCRIPT_DIR/00_fetch_vierstra_v1_resources.sh"
python3 "$SCRIPT_DIR/01_prepare_inputs.py"
python3 "$SCRIPT_DIR/02_scan_all_models.py"
python3 "$SCRIPT_DIR/03_collapse_to_archetypes.py"
bash "$SCRIPT_DIR/04_finalize_index_qc.sh"

echo "[cyno-motif] done: ${GET_CYNO_MOTIF_PREFIX}.bed.gz"
