# Troubleshooting

## User site packages leak into the container

Use `PYTHONNOUSERSITE=1`. The wrapper scripts set this automatically. Without it, user-local packages can shadow the container packages and break Torch or zarr.

## Seurat is missing in the container

This is expected. Run `tutorials/prepare_multiome1_human.R` on host R via:

```bash
bash scripts/course_01_prepare_multiome1.sh
```

Then run all Python steps in the container.

## Apptainer image is missing

Create it with:

```bash
mkdir -p $GET_COURSE_WORK/container
apptainer pull $GET_SIF docker://fuxialexander/get_model:latest
```

If the teaching server has no internet access, ask for a pre-staged `get.sif` and set:

```bash
export GET_SIF=/path/to/shared/get.sif
```

## Out of memory during fine-tuning

Lower the batch size:

```bash
export GET_BATCH_SIZE=8
bash scripts/course_03_finetune_lora.sh
```

If needed, also try:

```bash
bash scripts/course_03_finetune_lora.sh training.use_fp16=true
```

## Fine-tuned inference cannot find the LoRA checkpoint

The default path is:

```text
$GET_COURSE_WORK/output/finetune_multiome1_human/lora_leaveout_neurons/checkpoints/best.ckpt
```

Override it with:

```bash
export GET_LORA_CKPT=/path/to/best.ckpt
bash scripts/course_05_infer_finetuned.sh
```

## Hydra says a path is missing

Run:

```bash
bash scripts/course_00_check_environment.sh
```

Most path issues are caused by `GET_COURSE_DATA`, `GET_COURSE_WORK`, or `GET_SIF` pointing at the wrong location.
