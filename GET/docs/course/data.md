# Data inventory

This repo should contain code and documentation only. Large inputs and generated artifacts live outside Git.

## Required input files

Default large-file layout:

```text
~/GET_course_data/
  multiome_1/
    seu_multi_list_macsCA_assay.RDS
  annotations/
    hg38.archetype_motifs.v1.0.bed.gz
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
  container/get.sif
  multiome_1/preprocessed/*.atac.bed
  multiome_1/preprocessed/*.rna.csv
  multiome_1/preprocessed/multiome1_human.zarr
  multiome_1/preprocessed/_motif_staging/
  output/
```

The `_motif_staging` directory can be deleted after zarr creation.

## Instructor transfer checklist

Before the course starts, copy the required input files into each student's `~/GET_course_data` with the layout shown above. If a shared read-only location is used instead, students can point the same environment variables in [setup.md](setup.md) at that location.
