#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_MULTIOME_RDS" "multiome1 Seurat RDS"
mkdir -p "$GET_COURSE_WORK/multiome_1/preprocessed"

"$GET_RSCRIPT" "$GET_REPO/tutorials/prepare_multiome1_human.R"
