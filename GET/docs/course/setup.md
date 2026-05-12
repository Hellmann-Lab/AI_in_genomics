# Setup and server layout

The course setup assumes that each student receives:

1. A copy of this Git repository in their home directory.
2. A separate large-file directory, defaulting to `~/GET_course_data`.
3. A working directory for generated files, defaulting to `~/GET_course_work`.

The repo should not contain generated artifacts. Students can remove and recreate `~/GET_course_work` without damaging the Git checkout.

## Environment variables

The wrapper scripts set sensible defaults, but all paths can be overridden:

```bash
export GET_REPO=$HOME/AI_in_genomics/GET
export GET_COURSE_DATA=$HOME/GET_course_data
export GET_COURSE_WORK=$HOME/GET_course_work
export GET_SIF=$GET_COURSE_WORK/container/get.sif
export GET_RSCRIPT=/opt/R/4.5.0/bin/Rscript
```

Specific file overrides are also supported:

```bash
export GET_MULTIOME_RDS=$GET_COURSE_DATA/multiome_1/seu_multi_list_macsCA_assay.RDS
export GET_MOTIF_BED=$GET_COURSE_DATA/annotations/hg38.archetype_motifs.v1.0.bed.gz
export GET_MOTIF_BED_INDEX=$GET_MOTIF_BED.tbi
export GET_PRETRAINED_CKPT=$GET_COURSE_DATA/checkpoints/regulatory_inference_checkpoint_fetal_adult/finetune_fetal_adult_leaveout_astrocyte/checkpoint-best.pth
export GET_MULTIOME_ZARR=$GET_COURSE_WORK/multiome_1/preprocessed/multiome1_human.zarr
```

## Container

The course was tested with the GET Apptainer image built from:

```bash
apptainer pull $GET_SIF docker://fuxialexander/get_model:latest
```

If the teaching server has no internet access during the course, pre-stage `get.sif` in each student's `GET_COURSE_WORK/container/` or provide a shared read-only path and set `GET_SIF` accordingly.

## R step

The Seurat extraction step runs on host R because the GET container does not include the needed Seurat/Signac stack:

```bash
$GET_RSCRIPT tutorials/prepare_multiome1_human.R
```

All later Python steps run inside the Apptainer image.

## Interactive Python

Students can use the server JupyterHub directly for analysis notebooks, or install the GET container kernel when they need the exact course Python environment:

```bash
cd ~/AI_in_genomics/GET
bash scripts/course_install_container_kernel.sh
```

Restart the JupyterHub server from the Hub control panel, then choose `GET container (course)` in a new Launcher. See [interactive_python.md](interactive_python.md) for details.
