# Reference run summary

This is a compact summary of the instructor test run used to derive the course scripts. It is included as context only. Students should recreate preprocessing, fine-tuning, inference, and analysis outputs themselves.

## Objective

The test run used multiome1 embryoid-body data to:

- extract human singlet cells from the Seurat RDS
- aggregate ATAC and RNA per cell type
- build a GET-format `multiome1_human.zarr`
- fine-tune GET with LoRA while holding out neurons
- run held-out neuron inference for the base and fine-tuned model

## Cell types

The current course preprocessing keeps cell types with at least 100 filtered singlet cells, retaining eight human cell types:

```text
cardiac_fibroblasts
cardiac_progenitor_cells
early_ectoderm
glial_cells
mesoderm_ii
neural_crest_i
neurons
smooth_muscle_cells
```

Neurons are used as the default held-out cell type. Hepatocytes are now skipped by the 100-cell filter because they had about 49 filtered cells in the instructor data.

## Historical instructor metrics

The original instructor smoke run compared held-out hepatocyte expression predictions from the base pretrained checkpoint and the LoRA fine-tuned checkpoint. The current course default should be rerun with held-out neurons, so these historical values are context only.

| model | genes | Pearson | Spearman | MSE | R2 |
|---|---:|---:|---:|---:|---:|
| base pretrained | 15238 | 0.123 | 0.130 | 1.398 | -1.213 |
| LoRA fine-tuned | 15238 | 0.767 | 0.766 | 0.260 | 0.588 |

These values are a sanity check, not a target to copy. Students should rerun the pipeline and then design their own analysis or comparison.

## Runtime and resource notes

- Fine-tuning was fast in the reference run: about 3.5 min/epoch.
- The course wrapper default, `GET_TRAIN_EPOCHS=10`, should therefore take about 35 min.
- Directly using or editing `get_model/config/training/finetune.yaml` leaves its `epochs: 50` default in play, which is about 3 h at this speed.
- GPU memory was not the limiting resource: the run used about 4.3 GB of a 48 GB GPU.
- A 1-epoch run already showed the base-to-fine-tuned improvement, so it is useful as a quick feedback loop before a longer run.

## Caveats

- The Seurat extraction step used host R because the container did not include Seurat/Signac.
- All Python container commands used `PYTHONNOUSERSITE=1`.
- Fine-tuned inference needs the LoRA checkpoint from the fine-tuning run.
- Longer training did not substantially improve the original held-out hepatocyte result in the instructor test; changing epochs alone is not a strong analysis.
