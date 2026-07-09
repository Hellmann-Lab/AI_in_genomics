#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/course_env.sh"

export GET_CYNO_ANNOT_DIR="${GET_CYNO_ANNOT_DIR:-$GET_COURSE_DATA/annotations/make_cyno}"
export GET_CYNO_FASTA="${GET_CYNO_FASTA:-$GET_CYNO_ANNOT_DIR/genome.fa}"
export GET_CYNO_GTF="${GET_CYNO_GTF:-$GET_CYNO_ANNOT_DIR/genes.gtf.gz}"
export GET_VIERSTRA_V1_DIR="${GET_VIERSTRA_V1_DIR:-$GET_CYNO_ANNOT_DIR/vierstra_v1}"

user_set_motif_prefix="${GET_CYNO_MOTIF_PREFIX+x}"
user_set_work_dir="${GET_CYNO_WORK_DIR+x}"
if [[ -n "${TEST_REGION:-}" ]]; then
  export GET_CYNO_MOTIF_PREFIX="${GET_CYNO_MOTIF_PREFIX:-$GET_CYNO_ANNOT_DIR/smoke.macFas6.archetype_motifs.v1.0}"
  export GET_CYNO_WORK_DIR="${GET_CYNO_WORK_DIR:-$GET_CYNO_ANNOT_DIR/work_smoke}"
else
  export GET_CYNO_MOTIF_PREFIX="${GET_CYNO_MOTIF_PREFIX:-$GET_CYNO_ANNOT_DIR/macFas6.archetype_motifs.v1.0}"
  export GET_CYNO_WORK_DIR="${GET_CYNO_WORK_DIR:-$GET_CYNO_ANNOT_DIR/work}"
fi

if [[ -n "${TEST_REGION:-}" && -n "$user_set_motif_prefix" ]]; then
  echo "[cyno-motif] TEST_REGION set; using explicit GET_CYNO_MOTIF_PREFIX=$GET_CYNO_MOTIF_PREFIX"
fi
if [[ -n "${TEST_REGION:-}" && -n "$user_set_work_dir" ]]; then
  echo "[cyno-motif] TEST_REGION set; using explicit GET_CYNO_WORK_DIR=$GET_CYNO_WORK_DIR"
fi

course_require_file "$GET_SIF" "Apptainer image"
course_require_file "$GET_CYNO_FASTA" "macFas6 FASTA"
course_require_file "$GET_CYNO_GTF" "macFas6/Liftoff GTF"
course_require_file "$GET_REPO/tutorials/human_motif_cluster_id" "GET human motif cluster order"

mkdir -p "$GET_CYNO_ANNOT_DIR" "$GET_VIERSTRA_V1_DIR" "$GET_CYNO_WORK_DIR"

course_apptainer bash -lc "cd \"$GET_REPO\" && PYTHONNOUSERSITE=1 bash scripts/make_cyno_motif_resource/run_all.sh"
