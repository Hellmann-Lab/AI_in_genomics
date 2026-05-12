# GET multiome1 course repo

This repository is the course copy of GET with the local multiome1 tutorial patches included. Students use it to recreate preprocessing, LoRA fine-tuning, and inference. Downstream analysis is intentionally left for the assignment.

## Start here

The teaching server should contain one copy of this repo in each student home, plus a separate data directory with the non-Git inputs. The default layout is:

```text
~/AI_in_genomics/GET/ # this course module
~/GET_course_data/    # transferred input data and pretrained checkpoint
~/GET_course_work/    # generated zarrs, checkpoints, inference outputs
```

From the repo root:

```bash
cd ~/AI_in_genomics/GET

bash scripts/course_00_check_environment.sh
bash scripts/course_01_prepare_multiome1.sh
bash scripts/course_02_build_zarr.sh
bash scripts/course_03_finetune_lora.sh
bash scripts/course_04_infer_base.sh
bash scripts/course_05_infer_finetuned.sh
```

The scripts use these defaults, which can be overridden before running them:

```bash
export GET_COURSE_DATA=$HOME/GET_course_data
export GET_COURSE_WORK=$HOME/GET_course_work
export GET_SIF=$GET_COURSE_WORK/container/get.sif
export GET_RSCRIPT=/opt/R/4.5.0/bin/Rscript
```

## What is in Git

- GET source code and the local course patches.
- Multiome1 preprocessing scripts.
- Hydra configs for the multiome1 run.
- Lightweight wrapper scripts under `scripts/`.
- Course documentation under `docs/course/`.

## What is not in Git

Generated or large files must stay outside Git:

- `get.sif`
- `multiome1_human.zarr`
- fine-tuned checkpoints
- inference zarr outputs
- notebook execution outputs
- the source Seurat RDS

See [docs/course/data.md](docs/course/data.md) for the exact expected large-file layout.

## More notes

- [Setup and server layout](docs/course/setup.md)
- [Data inventory](docs/course/data.md)
- [Pipeline details](docs/course/pipeline.md)
- [Troubleshooting](docs/course/troubleshooting.md)
- [Reference run summary](docs/course/multiome1_reference_run_summary.md)

## Upstream GET

This course repo is based on the GET implementation from the [GET Foundation repository](https://github.com/GET-Foundation/get_model), described in "A foundation model of transcription across human cell types", Nature 2024. Keep the upstream license and citation in mind when reusing the code outside the course.
