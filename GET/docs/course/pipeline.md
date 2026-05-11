# Pipeline details

The student-facing path has five runnable stages. Each wrapper sources `scripts/course_env.sh`, so the same environment variables are used throughout.

## 0. Check environment

```bash
bash scripts/course_00_check_environment.sh
```

This checks the repo path, data path, host R, Apptainer image, source RDS, motif BED, and pretrained checkpoint.

## 1. Prepare cell-type ATAC/RNA files

```bash
bash scripts/course_01_prepare_multiome1.sh
```

This runs `tutorials/prepare_multiome1_human.R` on host R. It extracts the human object from the Seurat RDS, keeps singlets with `final_annotation`, aggregates ATAC/RNA per cell type, and writes:

```text
$GET_COURSE_WORK/multiome_1/preprocessed/<celltype>.atac.bed
$GET_COURSE_WORK/multiome_1/preprocessed/<celltype>.rna.csv
$GET_COURSE_WORK/multiome_1/preprocessed/celltypes.txt
```

## 2. Build GET zarr

```bash
bash scripts/course_02_build_zarr.sh
```

This runs `tutorials/build_multiome1_human_zarr.py` inside the GET container and writes:

```text
$GET_MULTIOME_ZARR
```

## 3. Fine-tune LoRA model

```bash
bash scripts/course_03_finetune_lora.sh
```

Defaults are intentionally course-sized:

```bash
GET_TRAIN_EPOCHS=10
GET_WARMUP_EPOCHS=1
GET_BATCH_SIZE=16
```

Students can override them before running:

```bash
export GET_TRAIN_EPOCHS=20
export GET_BATCH_SIZE=8
bash scripts/course_03_finetune_lora.sh
```

The default output checkpoint is:

```text
$GET_COURSE_WORK/output/finetune_multiome1_human/lora_leaveout_hepatocytes/checkpoints/best.ckpt
```

## 4. Base inference

```bash
bash scripts/course_04_infer_base.sh
```

This runs held-out hepatocyte inference from the pretrained checkpoint.

## 5. Fine-tuned inference

```bash
bash scripts/course_05_infer_finetuned.sh
```

This runs the same held-out hepatocyte inference with the LoRA checkpoint from stage 3.

## After inference

Students should recreate their own analyses from the inference zarrs. Example analysis ideas:

- per-gene prediction quality
- per-chromosome prediction quality
- base vs fine-tuned comparison
- motif attribution from jacobians
- sensitivity to held-out cell type or training hyperparameters
