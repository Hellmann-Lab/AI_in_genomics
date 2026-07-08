#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"
course_require_file "$GET_MOTIF_BED" "motif BED"
course_require_file "$GET_MOTIF_BED_INDEX" "motif BED tabix index"
course_require_file "$GET_PREPROCESSED_DIR/celltypes.txt" "preprocessed celltypes.txt"

if [[ "$GET_ZARR_BUILDER" = /* ]]; then
  course_require_file "$GET_ZARR_BUILDER" "zarr builder"
  builder_path="$GET_ZARR_BUILDER"
else
  course_require_file "$GET_REPO/tutorials/$GET_ZARR_BUILDER" "zarr builder"
  builder_path="$GET_REPO/tutorials/$GET_ZARR_BUILDER"
fi

course_apptainer bash -lc "cd \"$GET_REPO/tutorials\" && PYTHONNOUSERSITE=1 python3 \"$builder_path\""
