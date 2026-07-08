#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

export GET_REPO="${GET_REPO:-$DEFAULT_REPO}"
GET_COURSE_DATA="${GET_COURSE_DATA:-$HOME/data/GET_course_data}"
if [[ -e "$GET_COURSE_DATA" ]]; then
  GET_COURSE_DATA="$(readlink -f "$GET_COURSE_DATA")"
fi
export GET_COURSE_DATA
export GET_COURSE_WORK="${GET_COURSE_WORK:-$HOME/GET_course_work}"
export GET_SIF="${GET_SIF:-$GET_COURSE_WORK/container/get.sif}"
export GET_RSCRIPT="${GET_RSCRIPT:-/opt/R/4.5.0/bin/Rscript}"

export GET_MULTIOME_RDS="${GET_MULTIOME_RDS:-$GET_COURSE_DATA/multiome_1/seu_multi_list_macsCA_assay.RDS}"
export GET_MOTIF_BED="${GET_MOTIF_BED:-$GET_COURSE_DATA/annotations/hg38.archetype_motifs.v1.0.bed.gz}"
export GET_MOTIF_BED_INDEX="${GET_MOTIF_BED_INDEX:-$GET_MOTIF_BED.tbi}"
export GET_PRETRAINED_CKPT="${GET_PRETRAINED_CKPT:-$GET_COURSE_DATA/checkpoints/regulatory_inference_checkpoint_fetal_adult/finetune_fetal_adult_leaveout_astrocyte/checkpoint-best.pth}"
export GET_PREPROCESSED_DIR="${GET_PREPROCESSED_DIR:-$GET_COURSE_WORK/multiome_1/preprocessed}"
export GET_MULTIOME_ZARR="${GET_MULTIOME_ZARR:-$GET_PREPROCESSED_DIR/multiome1_human.zarr}"
export GET_LORA_CKPT="${GET_LORA_CKPT:-$GET_COURSE_WORK/output/finetune_multiome1_human/lora_leaveout_neurons/checkpoints/best.ckpt}"

export GET_PREPARE_SCRIPT="${GET_PREPARE_SCRIPT:-prepare_multiome1_human.R}"
export GET_ZARR_BUILDER="${GET_ZARR_BUILDER:-build_multiome1_human_zarr.py}"
export GET_CONFIG_NAME="${GET_CONFIG_NAME:-own_finetune_multiome1_human}"
export GET_ASSEMBLY="${GET_ASSEMBLY:-hg38}"
export GET_GENCODE_VERSION="${GET_GENCODE_VERSION:-40}"
export GET_GTF="${GET_GTF:-}"
export GET_GTF_ID_OR_NAME="${GET_GTF_ID_OR_NAME:-gene_name}"
export GET_PROMOTER_EXTEND_BP="${GET_PROMOTER_EXTEND_BP:-300}"
export GET_BASE_INFER_RUN_NAME="${GET_BASE_INFER_RUN_NAME:-interpret_base_neurons}"
export GET_FINETUNED_INFER_RUN_NAME="${GET_FINETUNED_INFER_RUN_NAME:-interpret_ft_neurons}"

export GET_TRAIN_EPOCHS="${GET_TRAIN_EPOCHS:-10}"
export GET_WARMUP_EPOCHS="${GET_WARMUP_EPOCHS:-1}"
export GET_BATCH_SIZE="${GET_BATCH_SIZE:-16}"

export PYTHONNOUSERSITE=1
export HYDRA_FULL_ERROR=1

mkdir -p "$GET_COURSE_WORK"

COURSE_BIND_ARGS=(
  -B "$GET_REPO:$GET_REPO"
  -B "$GET_COURSE_DATA:$GET_COURSE_DATA"
  -B "$GET_COURSE_WORK:$GET_COURSE_WORK"
)

course_apptainer() {
  apptainer exec --nv "${COURSE_BIND_ARGS[@]}" "$GET_SIF" "$@"
}

course_require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -e "$path" ]]; then
    echo "[missing] $label: $path" >&2
    return 1
  fi
}
