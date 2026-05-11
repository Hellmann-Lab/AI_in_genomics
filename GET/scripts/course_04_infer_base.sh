#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"
course_require_file "$GET_MULTIOME_ZARR" "multiome1 zarr"
course_require_file "$GET_PRETRAINED_CKPT" "pretrained checkpoint"

course_apptainer bash -lc "cd \"$GET_REPO\" && PYTHONNOUSERSITE=1 HYDRA_FULL_ERROR=1 python3 -m get_model.debug.debug_run_region_zarr --config-name own_finetune_multiome1_human stage=predict task.test_mode=interpret task.gene_list=null run.run_name=interpret_base_hepatocytes $*"
