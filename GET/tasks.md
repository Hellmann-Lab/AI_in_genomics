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

## 2. Run inference with the pretrained GET model

Here, we want to run inference using the pretrained GET model, i.e. predict gene expression using the pretrained model and cell-type-specific ATAC data.

How can that be done? What options are there? Have a look at `scripts/course_04_infer_base.sh`.

Decide on one configuration that you want to use: parameters, input data, etc.

Run inference.

Look at the output. What information do the different files contain?

Where is your predicted gene expression data?

Since you have multiome data, you can compare the predicted expression given your ATAC data with the observed expression. How well does it match?

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

You could now look at what motifs matter for a specific cell type and whether these match cell-type-specific motifs. You could also compare across species whether motif or region importance changes.

## 8. *In silico* perturbation

Perturbations are a common method in molecular and computational biology, where we change, or perturb, one particular feature and observe how this affects our measurements. This can help us learn about the function of the perturbed feature.

In this case, we could perturb either the ATAC data directly, e.g. by deleting an ATAC peak near an important gene, or mask a motif family, e.g. a cell-type-specific enhancer.

Then we could re-run inference and check how this changes the predicted expression. Does this change seem sensible for the perturbation? Do you think the model correctly models the effect of these perturbations?
