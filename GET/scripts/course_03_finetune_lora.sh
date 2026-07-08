#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/course_env.sh"

course_require_file "$GET_SIF" "Apptainer image"
course_require_file "$GET_MULTIOME_ZARR" "multiome1 zarr"
course_require_file "$GET_PRETRAINED_CKPT" "pretrained checkpoint"

course_apptainer bash -lc "cd \"$GET_REPO\" && PYTHONNOUSERSITE=1 HYDRA_FULL_ERROR=1 python3 -m get_model.debug.debug_run_region_zarr --config-name \"$GET_CONFIG_NAME\" stage=fit training.epochs=$GET_TRAIN_EPOCHS training.warmup_epochs=$GET_WARMUP_EPOCHS machine.batch_size=$GET_BATCH_SIZE $*"
