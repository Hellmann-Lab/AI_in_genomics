#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_MULTIOME_RDS" "multiome1 Seurat RDS"
course_require_file "$GET_REPO/tutorials/$GET_PREPARE_SCRIPT" "preparation script"
mkdir -p "$GET_PREPROCESSED_DIR"

"$GET_RSCRIPT" "$GET_REPO/tutorials/$GET_PREPARE_SCRIPT"
