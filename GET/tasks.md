# Tasks for GET

The following tasks should guide you through the application of GET. You should start from the beginning, and all work through the first tasks. After the first tasks, you can decide what you want to spend more, less, or no time on, and how you want to split the work between group members. Especially the later tasks are more intended as ideas of what you could do instead of tasks that you need to finish. For most tasks, there is not one single correct solution, but many different ways to approach each question.

What matters in the end is that you have a **nice coherent story of the application of GET** that you can present, **not whether you finished all tasks**. Working through all tasks in detail would probably take you much, much longer than these two weeks.

In this **second week**, at the end of each day, we expect each of you to **submit a short unstructured report** on:

1. what you did that day,
2. what the results were, and
3. your interpretation.

Ideally, you already thought about that during the day and only spend a few minutes writing it down.

In the third week, you have more time to work on your chosen analysis/tasks. On the **last Friday**, you should present what you did and learned **as a group in one coherent story** in 30–60 minutes. It is less about the time and more about the content.

In this course, we want you to learn how you can use these models and what they can or cannot do, not how to write nice code. So, **please do use LLMs for coding** and spend more time thinking about what to do and what the results tell you.

## 0. Setup

All scripts for using GET are gathered in a GitHub repository: https://github.com/Hellmann-Lab/AI_in_genomics/
Clone it into your home directory, so that it ends up at `~/AI_in_genomics`:

```bash
cd ~
git clone https://github.com/Hellmann-Lab/AI_in_genomics.git
cd ~/AI_in_genomics/GET
```

For you, only the `GET` subfolder (`~/AI_in_genomics/GET`) is relevant. Unless stated otherwise, all paths below are relative to that folder, so always work from `~/AI_in_genomics/GET`.

You work with three locations:

* `~/AI_in_genomics/GET` — the repository you cloned (code, scripts, docs).
* `~/data/GET_course_data` — the large input files we prepared for you (multiome dataset, motif annotations, pretrained checkpoint). This is a shared data folder reachable through the `data` symlink in your home; treat it as read-only and write your own outputs to `~/GET_course_work` instead.
* `~/GET_course_work` — where everything you generate (the `.zarr`, fine-tuned checkpoints, inference outputs) is written. You can delete and recreate it without touching the repo or the input data.

Get familiar with the repository that you cloned.

* What does it contain?
* What is an Apptainer? Download the Apptainer image. See `docs/course/setup.md`.
* What does `scripts/course_00_check_environment.sh` do? Run it. Any issues?

The `docs/course/` folder is your reference: `setup.md` (paths and container), `pipeline.md` (overview of the five wrapper scripts), `data.md` (what lives in `~/data/GET_course_data` and `~/GET_course_work`), `troubleshooting.md`, and `multiome1_reference_run_summary.md` (a compact summary of our own test run, for context and a rough sanity check of the numbers).

GET itself, including data preprocessing, inference, and fine-tuning, only runs stably inside the Apptainer. Everything else, such as looking at the outputs and creating plots, can be run inside the container, but you do not have to.

The scripts in `scripts/` were tested before and should work without problems if you use them as described. You do not have to use them, but they might help you, since using the model is not entirely straightforward.

`tutorials/` is a mix of helpful descriptions, tutorials from the original repository, and test scripts from us. See the `.md` files in particular. Some of these scripts are executed by the scripts in `scripts/`.

`get_model/` contains the core scripts from the original repository used to run GET.

You can change any file you want, but since many scripts call other scripts, it is usually safer to copy files before modifying them.

**How you actually run GET.** You never call GET's Python directly. Each `scripts/course_0*.sh` wrapper prepares the environment, launches the Apptainer container, and calls the same underlying GET entry point. What GET does is controlled entirely by [Hydra](https://hydra.cc) config files under `get_model/config/`, so you only ever edit YAML or pass command-line overrides, never the model code. Any extra arguments you append to a wrapper are forwarded straight to Hydra as dotted `key=value` overrides (there is an example in Step 3). Everything a run generates — checkpoints, logs, predictions, and plots — is written under `~/GET_course_work/output/`. See `tutorials/Configuration.md` for the full list of configurable options and `docs/course/pipeline.md` for the exact output paths.

## 1. Understanding the dataset

Your dataset for this week is a multiome dataset from embryoid bodies. Multiome means that for each cell, you have both ATAC-seq (= accessibility) and RNA-seq (= expression) data. Embryoid bodies form when induced pluripotent stem cells (iPSCs) are left to differentiate in an undirected manner. They form small aggregates of cells from all three germ layers. The longer they are left to differentiate, the more specialized cell types appear. In this case, differentiation was 16 days.

Look at the multiome dataset.

* What type of data does it contain?
* Cells from which species are in there?
* What cell types are in there?
* Make a visual overview showing how many cells per cell type and species exist in this data.
* Do all cell types exist in both species?

The dataset contains embeddings in `@reductions`. Make a plot showing one of them.

Prepare the dataset for GET. This happens in two steps, both of which write into `~/GET_course_work`. First, `scripts/course_01_prepare_multiome1.sh` extracts the human cells from the Seurat object and aggregates ATAC/RNA per cell type. Then `scripts/course_02_build_zarr.sh` turns that into the `.zarr` file that GET reads (`course_02` needs the output of `course_01`, so run them in order). Explain in your own words what was done in these steps. For now, use only human data.

Hints for exploring the dataset:

* The Seurat object is at `~/data/GET_course_data/multiome_1/seu_multi_list_macsCA_assay.RDS` (env var `GET_MULTIOME_RDS`). It is a **named list of Seurat objects, one per species** — `readRDS(...)` then `names(listObj)` shows the species; `listObj$human` is the human object.
* The relevant metadata columns (`listObj$human@meta.data`) are `final_annotation` (the cell-type label used downstream), `doubletCall` (keep `"singlet"`), and the species. Use these to build the per-cell-type / per-species counts.
* For the cells-per-cell-type-and-species overview, pull `@meta.data` from each species object into one data frame and plot with ggplot; use `facet_wrap(~species)` (per your facet rule) for the bar chart.
* The embeddings live in `listObj$human@reductions` (e.g. UMAP). Plot with `Seurat::DimPlot(listObj$human, reduction = "umap", group.by = "final_annotation")`.

Hints for the two preparation steps (so you can explain them):

* `course_01` runs `tutorials/prepare_multiome1_human.R` on the **host R** (not the container — it needs Seurat/Signac). It: keeps `final_annotation != NA & doubletCall == "singlet"`; keeps only `chr*` peaks (drops `chrM`, `chrY`, `chrUn*`, and `_`/alt contigs); drops cell types with `< min_cells` (`min_cells <- 100`, which removes e.g. hepatocytes 49 cells); computes a normalized ATAC score (`aTPM`) and RNA `TPM` per cell type. It writes `<celltype>.atac.bed`, `<celltype>.rna.csv`, and `celltypes.txt` into `~/GET_course_work/multiome_1/preprocessed/`.
* The eight retained human cell types are: `cardiac_fibroblasts, cardiac_progenitor_cells, early_ectoderm, glial_cells, mesoderm_ii, neural_crest_i, neurons, smooth_muscle_cells`.
* `course_02` runs `tutorials/build_multiome1_human_zarr.py` **inside the container** and produces `~/GET_course_work/multiome_1/preprocessed/multiome1_human.zarr` (env var `GET_MULTIOME_ZARR`). It scans the motif BED (`GET_MOTIF_BED = hg38.archetype_motifs.v1.0.bed.gz`) over the peaks and attaches expression from GENCODE v40.
* Per your Rscript rule, if you write your own R exploration, run it with `/opt/R/4.5.0/bin/Rscript` (the course default `GET_RSCRIPT`).

## 2. Run inference with the pretrained GET model

Here, we want to run inference using the pretrained GET model, i.e. predict gene expression using the pretrained model and cell-type-specific ATAC data.

How can that be done? What options are there? Have a look at `scripts/course_04_infer_base.sh`.

Decide on one configuration that you want to use: parameters, input data, etc.

Run inference.

Look at the output. What information do the different files contain?

Where is your predicted gene expression data?

Since you have multiome data, you can compare the predicted expression given your ATAC data with the observed expression. How well does it match?

Hints:

* `scripts/course_04_infer_base.sh` runs the pretrained checkpoint (`GET_PRETRAINED_CKPT`) with the same config as fine-tuning (`own_finetune_multiome1_human`) but with `stage=predict task.test_mode=interpret task.gene_list=null run.run_name=interpret_base_neurons`. It predicts expression for the **held-out cell type** set by `leave_out_celltypes` in `get_model/config/dataset/multiome1_human.yaml` (default `neurons`).
* Options you can decide on and pass as Hydra overrides after the script name:
  * `task.gene_list=null` predicts all genes; set e.g. `task.gene_list=MYC,SOX10,SOX2` to focus on a few.
  * `dataset.leave_out_celltypes=<celltype>` picks which cell type is predicted (must be one of the eight; this is the cell type held back for evaluation).
  * `run.run_name=<name>` names the output folder (otherwise you overwrite `interpret_base_neurons`).
* The output goes to `~/GET_course_work/output/finetune_multiome1_human/interpret_base_neurons/<celltype>.zarr` (e.g. `neurons.zarr`). Inside, the obs/pred arrays have shape `(n_samples, 200, 2)` (200 regions per sample, 2 = the two strands/TSS outputs); the interpret run also stores `jacobians/...` and the `input/region_motif` used in Step 7.
* Your **predicted expression** is in that `.zarr`; your **observed expression** is the `<celltype>.rna.csv` (column `TPM`) written in Step 1.
* Easiest way to read the zarr and collapse it to one value per gene: adapt `tutorials/compare_base_vs_finetuned.ipynb`, which already loads the interpret zarr and does the strand-aware per-gene collapse. For the observed-vs-predicted scatter/correlation, use ggplot in R (per your rules).

## 3. Fine-tuning

We can fine-tune the pretrained model using data that are more similar to the data we want to predict. We do not want to use the exact same data for fine-tuning and inference, so we need to create a split where some data are used for fine-tuning and some data are left out for validation.

There are different ways of splitting the data, e.g. leaving out one cell type or leaving out one chromosome. For your first run, I recommend **leaving out one cell type with enough cells**. This means that you fine-tune the model on the other cell types and then test whether prediction improves for the left-out cell type.

Think about how you want to split your data. Try to answer:

* Which cell types do you use for fine-tuning?
* Which cell type or chromosome do you leave out?
* What biological question does this split test?

Fine-tuning is run with `scripts/course_03_finetune_lora.sh`. Its default configuration lives in `get_model/config/own_finetune_multiome1_human.yaml`, and the data split (which cell types, what is left out) is defined in `get_model/config/dataset/multiome1_human.yaml`. Have a look at both before you start.

You can change parameters either by editing those YAML files or by appending Hydra overrides to the wrapper, for example:

```bash
bash scripts/course_03_finetune_lora.sh dataset.leave_out_celltypes=glial_cells training.epochs=20
```

Do not change the model architecture (number of layers, embedding size, number of motifs). Those are fixed by the pretrained checkpoint, and changing them will stop the checkpoint from loading.

Start with the default fine-tuning configuration. Only change the parameters that are necessary for your split, especially:

| Key                     | Meaning                                                         |
| ----------------------- | --------------------------------------------------------------- |
| `zarr_path`             | Path to your `.zarr` file from Step 1                           |
| `celltypes`             | Cell types used for fine-tuning                                 |
| `leave_out_celltypes`   | Cell type held out for validation                               |
| `leave_out_chromosomes` | Chromosome(s) held out for validation                           |
| `use_lora`              | Use LoRA adapters instead of full fine-tuning; recommended      |
| `epochs`                | Number of fine-tuning epochs                                    |
| `batch_size`            | Number of samples per batch; lower if you run out of GPU memory |
| `run_name`              | Informative name for your run                                   |

Exactly one of `leave_out_celltypes` or `leave_out_chromosomes` should usually be set. Do not try to tune many parameters at once.

Recommended first run:

```yaml
finetune:
  use_lora: true
  strict: true
  layers_with_lora: ['region_embed', 'encoder']
  patterns_to_freeze: ["motif_scanner"]

training:
  epochs: 10
  warmup_epochs: 1
  save_ckpt_freq: 1
  use_fp16: false

optimizer:
  lr: 1e-4
  weight_decay: 0.05
```

Run fine-tuning. Depending on your data and parameter choice, this may run for a few hours. Coordinate within your group so only one person starts the first run. Also coordinate with other groups, since GPU resources are limited.

Concrete hints:

* The three most common knobs are already wired to env vars in `course_env.sh`, so you can set them without editing YAML: `GET_TRAIN_EPOCHS` (default 10), `GET_WARMUP_EPOCHS` (default 1), `GET_BATCH_SIZE` (default 16, lower to 8/4 if you hit GPU out-of-memory). The wrapper also forwards any extra Hydra overrides you append, e.g. `dataset.leave_out_celltypes=glial_cells`.
* The split lives entirely in `get_model/config/dataset/multiome1_human.yaml`: `celltypes` (the training set) and `leave_out_celltypes` (default `neurons`). The held-out cell type should still appear in `celltypes` — GET trains on the others and evaluates the held-out one.
* **Important path coupling:** the run writes its checkpoint to `~/GET_course_work/output/finetune_multiome1_human/<run.run_name>/checkpoints/best.ckpt`, and `run.run_name` defaults to `lora_leaveout_neurons` (in `own_finetune_multiome1_human.yaml`). The default `GET_LORA_CKPT` in `course_env.sh` points at exactly that path. If you change the held-out cell type (and therefore `run.run_name`), update `GET_LORA_CKPT` to match, or Step 5 will load the wrong / a missing checkpoint.
* Sanity check against `docs/course/multiome1_reference_run_summary.md`: on held-out neurons you should see the fine-tuned model clearly beat the base model (the instructor smoke run on held-out hepatocytes went from Pearson ~0.12 base to ~0.77 fine-tuned). Treat these as a rough sanity check, not a target.
* Note from the reference run: simply increasing `epochs` did **not** substantially improve the result — so "more epochs" alone is not a strong analysis; changing the split is more informative.

While the model is training, the others can already prepare the validation analysis and look more closely at the pretrained inference output.

When fine-tuning has finished, run inference again on the left-out validation data using your fine-tuned model. This is done with `scripts/course_05_infer_finetuned.sh` (the fine-tuned counterpart of `scripts/course_04_infer_base.sh` from Step 2). Then compare:

1. observed expression,
2. prediction from the pretrained model (`course_04`),
3. prediction from the fine-tuned model (`course_05`).

Ask: **Did fine-tuning improve expression prediction on data that were not used for fine-tuning?**

If the first run worked and the server has resources, you can compare simple fine-tuning options, e.g. different left-out cell types, different numbers of epochs, or LoRA vs. full fine-tuning. Change only one major thing at a time, so that you can interpret the result.

## 4. Validation

Compare predicted expression between the pretrained and the fine-tuned model.

The main question is:

> Did fine-tuning improve expression inference on data that were not used for fine-tuning?

`tutorials/compare_base_vs_finetuned.ipynb` is a starting template for reading the base and fine-tuned inference outputs and comparing them; you can adapt it to your own split.

Hints on inputs and where things come from:

* The notebook reads the two interpret zarrs from Steps 2 and 3: `.../interpret_base_neurons/<celltype>.zarr` (base) and `.../interpret_ft_neurons/<celltype>.zarr` (fine-tuned). If you used a different split, point it at the right folders with the env vars `GET_BASE_INTERPRET_ZARR`, `GET_FT_INTERPRET_ZARR`, and set `GET_COMPARE_OUT_DIR` for the figures.
* It already collapses the `(n_samples, 200, 2)` arrays to one observed and one predicted value per gene (strand-aware) and computes Pearson/Spearman/R²/MSE — reuse that collapse, then do plotting in R/ggplot per your rules.
* Observed expression is the `<celltype>.rna.csv` (column `TPM`) from Step 1. For the baselines: **mean expression** = average `TPM` across the training cell types' `.rna.csv` files; **TSS accessibility baseline** = the `aTPM` near each gene's TSS from the `<celltype>.atac.bed`; **most similar training cell type** = the training `.rna.csv` most correlated with the held-out one.
* For the advanced ABC-style distance baseline, `tutorials/distance_model_comparison.py` reads the fine-tuned interpret zarr (override with `GET_FT_INTERPRET_ZARR`) and writes to `output/finetune_multiome1_human/distance_model_comparison/`.
* Use `patchwork` to combine the scatter/barplot/heatmap panels, and `facet_wrap`/`facet_grid` when showing the same plot for base vs fine-tuned or across cell types (per your rules).

Start with simple comparisons between observed and predicted expression:

* Make a scatterplot of observed vs. predicted expression.
* Calculate Pearson and/or Spearman correlation.
* Compare the pretrained model and the fine-tuned model using the same validation data.
* Look separately at the left-out cell type or chromosome that was not used during fine-tuning.

Also compare the expression prediction by GET to simple baselines, for example:

* mean expression across the training cell types,
* TSS accessibility / ATAC signal near the gene,
* the most similar training cell type.

Does GET outperform these simple baselines? Fine-tuning is only clearly useful if it improves over both the pretrained model and at least one simple baseline. For a more advanced distance/accessibility (ABC-style) baseline, `tutorials/distance_model_comparison.py` is an optional example you can build on.

Then look more closely at the errors.

* Which genes are predicted well?
* Which genes are predicted poorly?
* Are highly expressed genes predicted better than lowly expressed genes?
* Are cell-type-specific genes predicted well?
* Are some cell types much easier or harder to predict than others?

Useful plots could be:

* observed vs. predicted expression scatterplots,
* correlation barplots comparing pretrained GET, fine-tuned GET, and baselines,
* histograms or boxplots of prediction errors,
* examples of well- and poorly predicted genes,
* heatmaps comparing observed and predicted pseudobulk expression across cell types.

Try to interpret the result biologically. For example, if some genes or cell types are predicted poorly, think about whether this could be due to weak ATAC signal, noisy RNA expression, missing cell types in the fine-tuning data, or limitations of the model.


## 5. Cell-type preservation

Our input data contains different cell types, which are the main source of variance between cells. Ideally, our predicted expression data should reproduce the cell type identities of our multiome data.

You can create pseudobulks, i.e. merge all cells of one cell type into one pseudo-cell, to simplify the analysis and visualization.

You could check whether cell types are preserved via:

* correlation matrices, i.e. how well each cell type correlates with each other cell type using expression data. Then you can compare whether the correlation matrix of the predicted data matches the correlation matrix of the input data.
* PCA / UMAP → clustering.

Hints:

* The **observed pseudobulks already exist**: each `<celltype>.rna.csv` (column `TPM`) from Step 1 is one pseudo-cell per cell type. Stacking the eight files gives you a genes × cell-types observed matrix.
* To get **predicted pseudobulks for every cell type**, you need one inference run per cell type, since inference predicts whichever cell type is held out. Loop `scripts/course_04_infer_base.sh` over the eight cell types, changing both the held-out cell type and the run name each time, e.g.:

```bash
for ct in cardiac_fibroblasts cardiac_progenitor_cells early_ectoderm glial_cells mesoderm_ii neural_crest_i neurons smooth_muscle_cells; do
  bash scripts/course_04_infer_base.sh dataset.leave_out_celltypes=$ct run.run_name=predict_base_$ct
done
```

  Then collapse each `.../predict_base_<ct>/<ct>.zarr` to one predicted value per gene (reuse the collapse from `tutorials/compare_base_vs_finetuned.ipynb`) to build the predicted genes × cell-types matrix.
* Build a cell-type × cell-type correlation matrix for both the observed and the predicted matrix (`cor()` in R), then compare them side by side — plot the two heatmaps together with `patchwork`. For PCA/UMAP, treat each cell-type pseudobulk as one point and check whether related cell types (e.g. the cardiac ones) cluster together in both observed and predicted space.

## 6. Species transfer

Until now, we have used only the human data, because the pretrained model was trained only on human data. Using the same motif vocabulary as GET, we created a cyno/macFas6 motif annotation. You can find it in:

```text
~/data/GET_course_data/annotations/make_cyno/
```

The important files are:

```text
macFas6.archetype_motifs.v1.0.bed.gz
macFas6.archetype_motifs.v1.0.bed.gz.tbi
genes.gtf.gz
```

See also `scripts/make_cyno_motif_resource/README.md` if you want to understand how the motif annotation was built. You do **not** need to rebuild it.

Your task is to adapt the human pipeline to cyno. The model code can already read a local GTF when you set `GET_GTF`, so you should not need to write a new GTF parser. The parts you do need to think about are the same parts a real analysis would require: which species object to use, which cell types to keep, how to name chromosomes, what data split to use, and how to compare the result.

Hints for the data-preparation step:

* Start from `tutorials/prepare_multiome1_human.R`, but copy it before changing it.
* Change the species/object selection from human to cyno.
* Check which metadata column contains the final cell-type labels for cyno.
* Write the same three kinds of files as before: `<celltype>.atac.bed`, `<celltype>.rna.csv`, and `celltypes.txt`.
* The cyno motif annotation and GTF use Ensembl-style contig names like `1`, `2`, ..., `X`, **not** `chr1`, `chr2`, ..., `chrX`. Your ATAC BED files must use the same naming.
* Keep the output in a separate work folder, for example under `~/GET_course_work/multiome_1_cyno/preprocessed`, so you do not overwrite your human `.zarr`.

Hints for building the cyno `.zarr`:

* The generic builder is `tutorials/build_multiome_zarr.py`.
* Point it at your cyno preprocessed files with `GET_PREPROCESSED_DIR`.
* Point it at the cyno motif BED with `GET_MOTIF_BED`.
* Point it at `genes.gtf.gz` with `GET_GTF`.
* Set `GET_MULTIOME_ZARR` to a cyno-specific output path.

Hints for the GET configuration:

* Use the template files:
  * `get_model/config/dataset/multiome1_cyno.template.yaml`
  * `get_model/config/own_finetune_multiome1_cyno.template.yaml`
* Copy the templates to real `.yaml` files before editing them.
* Replace the TODOs with your actual cell types, held-out cell type/chromosome, and run name.
* Keep `assembly: macFas6` in the cyno top-level config.
* Use `GET_CONFIG_NAME` to tell the course wrappers which config to run.

As before, evaluate how well inference worked: without fine-tuning, with human fine-tuning, and with cyno fine-tuning. For cyno fine-tuning, choose a validation split that you can explain biologically. For example, leave out one cyno cell type with enough cells and ask whether cyno fine-tuning improves prediction for that cell type.

Compare human–cyno inference performance. Are there cell types or genes that transfer particularly well or not well? Can you find an explanation for those?

## 7. Regulatory interpretation

Using the inference output, you can quantify feature contribution, i.e. which feature matters how much for predicting a gene's expression. You can use the Jacobian, which is an optional output during the inference run. The Jacobian essentially tells you: “Would the prediction of this TSS or gene change if this feature in this region changed?” If we multiply this by the input, we get a matrix that is directly relevant for our specific data, telling us: “How much does this observed motif feature in this region contribute to this TSS?”

We can aggregate this over all motifs per region, telling us how much each region affects the expression of each TSS.

Alternatively, we can aggregate over all regions per motif, telling us how much each motif affects the expression of each TSS.

You can see an example of this in `GET/tutorials/jacobian_analysis_neurons.ipynb`. You can adapt this directly to your dataset.

Hints:

* The Jacobian is produced automatically by the interpret runs from Steps 2/3 (that is what `task.test_mode=interpret` does), so you do **not** need a separate run — just reuse the `interpret_base_neurons/<celltype>.zarr` and `interpret_ft_neurons/<celltype>.zarr` outputs. Inside the zarr the arrays are at `jacobians/exp/{0,1}/input/region_motif`, with **283 channels** = 282 motif clusters + 1 accessibility channel.
* The notebook already implements the two aggregations: the gene × motif contribution as `mean over regions r of jacobian[r,m] · input[r,m]`, and the per-region contribution as the sum over motifs. Point it at your zarrs with `GET_BASE_INTERPRET_ZARR` / `GET_FT_INTERPRET_ZARR`, set `GET_HOLDOUT_RNA_CSV` to your held-out `<celltype>.rna.csv`, and `GET_JACOBIAN_OUT_DIR` for figures.
* To focus the Jacobian on specific genes (cheaper and easier to read), rerun inference with e.g. `task.gene_list=MYC,SOX10,SOX2,RET` instead of `task.gene_list=null`.
* The motif channel names come from `tutorials/human_motif_cluster_id`; use it to map channel indices back to TF/motif-cluster names when you ask "which motifs matter for this cell type".
* For the cross-species comparison (Step 6), run the same notebook on the cyno interpret zarrs and compare motif/region importance for matched cell types.

## 8. *In silico* perturbation

Perturbations are a common method in molecular and computational biology, where we change, or perturb, one particular feature and observe how this affects our measurements. This can help us learn about the function of the perturbed feature.

In this case, we could perturb either the ATAC data directly, e.g. by deleting an ATAC peak near an important gene, or mask a motif family, e.g. a cell-type-specific enhancer.

Then we could re-run inference and check how this changes the predicted expression. Does this change seem sensible for the perturbation? Do you think the model correctly models the effect of these perturbations?

Hints:

* There is no dedicated perturbation script — you build it yourself from the existing pipeline. The simplest ATAC perturbation works on the preprocessed files:
  1. Copy your preprocessed folder to a new one (so you keep the unperturbed baseline), e.g. `~/GET_course_work/multiome_1/preprocessed_perturb/`.
  2. In the relevant `<celltype>.atac.bed`, find the peak(s) near your target gene's TSS and set the `aTPM` value (4th column) to `0`, or drop the peak. Keep contig naming consistent (`chr*` for human).
  3. Point `GET_PREPROCESSED_DIR` and a new `GET_MULTIOME_ZARR` (e.g. `..._perturb.zarr`) at the copy and rebuild the zarr with `scripts/course_02_build_zarr.sh`.
  4. Re-run inference (`scripts/course_04_infer_base.sh`, with a distinct `run.run_name`) on the perturbed zarr and compare predicted expression of the target gene (and neighbours) against the unperturbed run.
* Choose a target where you expect a clear effect: a strongly cell-type-specific gene with a nearby accessible, high-importance peak (use the Step 7 Jacobian/region importance to pick a peak that the model says matters).
* A motif-family perturbation is the more advanced variant: instead of editing a peak, zero out one motif channel in the `input/region_motif` matrix before the model forward pass. This is a code-level change, so start with the ATAC-peak perturbation above.
* Interpret carefully: because you rebuild the zarr, the peak set feeding the region embedding also changes — compare against the matched unperturbed run, not across different splits.
