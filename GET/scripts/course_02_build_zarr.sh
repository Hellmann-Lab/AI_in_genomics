#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"
course_require_file "$GET_MOTIF_BED" "motif BED"
course_require_file "$GET_COURSE_WORK/multiome_1/preprocessed/celltypes.txt" "preprocessed celltypes.txt"

course_apptainer bash -lc "cd \"$GET_REPO/tutorials\" && PYTHONNOUSERSITE=1 python3 build_multiome1_human_zarr.py"
