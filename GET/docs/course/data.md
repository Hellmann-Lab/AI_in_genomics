# Data inventory

This repo should contain code and documentation only. Large inputs and generated artifacts live outside Git.

## Required input files

Default large-file layout:

```text
~/data/GET_course_data/
  container/
    get.sif
  multiome_1/
    seu_multi_list_macsCA_assay.RDS
  annotations/
    hg38.archetype_motifs.v1.0.bed.gz
    hg38.archetype_motifs.v1.0.bed.gz.tbi
  checkpoints/
    regulatory_inference_checkpoint_fetal_adult/
      finetune_fetal_adult_leaveout_astrocyte/
        checkpoint-best.pth
```

The repo itself already contains the small GET reference files under `data/`, including the GENCODE files needed by `gcell`.

## Generated files

These are recreated by students and should not be provided as Git-tracked files:

```text
~/GET_course_work/
  multiome_1/preprocessed/*.atac.bed
  multiome_1/preprocessed/*.rna.csv
  multiome_1/preprocessed/multiome1_human.zarr
  multiome_1/preprocessed/_motif_staging/
  output/
```

The `_motif_staging` directory can be deleted after zarr creation.

## Instructor transfer checklist

Before the course starts, copy the required input files into `/data/GET_course_data` (reachable from every home as `~/data/GET_course_data`) with the layout shown above. The Apptainer image should be downloaded once to `container/get.sif` in that shared data directory.
