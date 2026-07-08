# Cyno macFas6 Vierstra motif resource

This workflow builds a macFas6 archetype motif BED comparable to the Vierstra
v1.0 human resource used by GET. The scripts are tracked in this repo; all large
inputs, downloads, intermediate scans, and final motif files stay under
`~/data/GET_course_data/annotations/make_cyno`.

Default inputs:

```text
~/data/GET_course_data/annotations/make_cyno/genome.fa
~/data/GET_course_data/annotations/make_cyno/genes.gtf.gz
```

Default outputs:

```text
~/data/GET_course_data/annotations/make_cyno/macFas6.archetype_motifs.v1.0.bed.gz
~/data/GET_course_data/annotations/make_cyno/macFas6.archetype_motifs.v1.0.bed.gz.tbi
~/data/GET_course_data/annotations/make_cyno/macFas6.archetype_motifs.v1.0.qc.md
```

Run a small smoke test first:

```bash
cd AI_in_genomics/GET
TEST_REGION=1:1-1000000 bash scripts/course_make_cyno_motif_resource.sh
```

When `TEST_REGION` is set, the wrapper defaults to smoke-test outputs:

```text
~/data/GET_course_data/annotations/make_cyno/smoke.macFas6.archetype_motifs.v1.0.bed.gz
~/data/GET_course_data/annotations/make_cyno/work_smoke/
```

Run the full resource:

```bash
cd AI_in_genomics/GET
bash scripts/course_make_cyno_motif_resource.sh
```

Useful controls:

```bash
FORCE=1                  # redownload/recompute existing outputs
MOTIF_BATCH_SIZE=64      # motifs per MOODS scan batch
SCAN_CHUNK_BP=10000000   # sequence chunk size per contig/region
THREADS=16               # external-sort parallelism
SORT_MEM=32G             # external-sort memory budget
KEEP_FULL_SCAN=1         # keep raw full-model scan shards
KEEP_ADJUSTED=1          # keep adjusted unsorted/sorted temporary files
```

The cyno FASTA/GTF and Seurat peaks use Ensembl-style contig names (`1`, `2`,
..., `X`) rather than UCSC `chr` names. The workflow preserves those names.
