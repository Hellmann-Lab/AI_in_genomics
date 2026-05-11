#!/usr/bin/env Rscript
# prepare_multiome1_human.R
#
# Extract the human Seurat from `seu_multi_list_macsCA_assay.RDS`,
# filter cells, and write per-celltype .atac.bed and .rna.csv files
# in the format expected by `preprocess_utils.py` (`add_atpm`, `add_exp`).
#
# Output dir (one file per cell type kept):
#   <out_dir>/<celltype>.atac.bed : Chromosome Start End aTPM (tab-separated, no header)
#   <out_dir>/<celltype>.rna.csv  : gene_name,TPM (comma-separated, with header)
#
# aCPM normalization (per cell type, matches prepare_pbmc.ipynb):
#     counts <- colSums aggregated per peak across cells of the cell type
#     aCPM   <- log10(counts/sum(counts)*1e5 + 1)
#     aCPM   <- aCPM / max(aCPM)    # => column is named aTPM in the output
#
# RNA normalization (per cell type):
#     counts <- rowSums aggregated per gene across cells of the cell type
#     TPM    <- log10(counts/sum(counts)*1e6 + 1)
#
# NOTE on execution:
# The apptainer container (`get.sif`) does not ship Seurat/Signac and
# bind-mounting /opt/R fails due to libblas mismatch, so this one R step
# has to run on the host with Seurat installed:
#     /opt/R/4.5.0/bin/Rscript tutorials/prepare_multiome1_human.R
# All downstream steps (zarr build, fine-tune, inference, comparison)
# run inside the apptainer container.

suppressPackageStartupMessages({
  library(Seurat)
  library(Signac)
  library(Matrix)
})

getenv_default <- function(name, default) {
  value <- Sys.getenv(name, unset = "")
  if (nzchar(value)) value else default
}

course_data <- getenv_default("GET_COURSE_DATA", file.path(Sys.getenv("HOME"), "GET_course_data"))
course_work <- getenv_default("GET_COURSE_WORK", file.path(Sys.getenv("HOME"), "GET_course_work"))

rds_path <- getenv_default(
  "GET_MULTIOME_RDS",
  file.path(course_data, "multiome_1", "seu_multi_list_macsCA_assay.RDS")
)
out_dir <- getenv_default(
  "GET_PREPROCESSED_DIR",
  file.path(course_work, "multiome_1", "preprocessed")
)
min_cells <- 30   # keep hepatocytes (~50) but drop very small groups (iPSCs=8, epithelial=18)

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

cat("[prepare] loading", rds_path, "\n")
listObj <- readRDS(rds_path)
stopifnot("human" %in% names(listObj))
seu <- listObj$human
rm(listObj); invisible(gc())

cat("[prepare] raw human cells:", ncol(seu),
    "RNA genes:", nrow(seu[["RNA"]]),
    "MACS peaks:", nrow(seu[["peaks"]]), "\n")

# Keep singlets with a final annotation.
md   <- seu@meta.data
keep <- !is.na(md$final_annotation) & md$doubletCall == "singlet"
cat("[prepare] cells after NA/doublet filter:", sum(keep),
    "/", length(keep), "\n")
seu <- seu[, keep]

# Standardize chromosome filter on the peak set.
peak_names <- rownames(seu[["peaks"]])
peak_parts <- do.call(rbind, strsplit(peak_names, "-"))
stopifnot(ncol(peak_parts) == 3)
chrom <- peak_parts[, 1]
start <- as.integer(peak_parts[, 2])
end   <- as.integer(peak_parts[, 3])

good_chrom <- grepl("^chr", chrom) &
              !(chrom %in% c("chrM", "chrY")) &
              !grepl("^chrUn", chrom) &
              !grepl("_", chrom)  # drop alt/random contigs like chr1_KI270...

cat("[prepare] peaks after chrom filter:", sum(good_chrom), "/", length(good_chrom), "\n")

peaks_counts_full <- GetAssayData(seu, assay = "peaks", layer = "counts")
peaks_counts_full <- peaks_counts_full[good_chrom, , drop = FALSE]
chrom <- chrom[good_chrom]
start <- start[good_chrom]
end   <- end[good_chrom]

# Sort peaks by chrom + start so downstream bed is sorted
ord   <- order(chrom, start, end)
peaks_counts_full <- peaks_counts_full[ord, , drop = FALSE]
chrom <- chrom[ord]
start <- start[ord]
end   <- end[ord]

rna_counts_full <- GetAssayData(seu, assay = "RNA", layer = "counts")
gene_names      <- rownames(rna_counts_full)

celltypes <- sort(unique(seu$final_annotation))
cat("[prepare] candidate cell types:\n")
print(table(seu$final_annotation))

sanitize <- function(x) {
  x <- tolower(x)
  x <- gsub("[^a-z0-9]+", "_", x)
  x <- gsub("^_+|_+$", "", x)
  x
}

kept_cts <- character(0)

for (ct in celltypes) {
  mask    <- !is.na(seu$final_annotation) & seu$final_annotation == ct
  n_cells <- sum(mask)
  ct_san  <- sanitize(ct)

  if (n_cells < min_cells) {
    cat(sprintf("[skip]  %-28s : %d cells < min_cells=%d\n",
                ct, n_cells, min_cells))
    next
  }

  # ---------- ATAC: cell-type aggregated peak counts ----------
  peak_counts <- Matrix::rowSums(peaks_counts_full[, mask, drop = FALSE])
  tot         <- sum(peak_counts)
  if (tot == 0) {
    cat(sprintf("[skip]  %-28s : no ATAC counts\n", ct))
    next
  }
  acpm     <- log10(peak_counts / tot * 1e5 + 1)
  max_acpm <- max(acpm)
  if (max_acpm == 0) {
    cat(sprintf("[skip]  %-28s : flat ATAC signal\n", ct))
    next
  }
  acpm_n <- acpm / max_acpm
  bed <- data.frame(
    Chromosome = chrom,
    Start      = start,
    End        = end,
    aTPM       = acpm_n
  )
  atac_path <- file.path(out_dir, paste0(ct_san, ".atac.bed"))
  write.table(bed, atac_path, sep = "\t",
              row.names = FALSE, col.names = FALSE, quote = FALSE)

  # ---------- RNA: cell-type aggregated gene counts ----------
  gene_counts <- Matrix::rowSums(rna_counts_full[, mask, drop = FALSE])
  g_tot       <- sum(gene_counts)
  if (g_tot == 0) {
    cat(sprintf("[warn]  %-28s : no RNA counts, writing zeros\n", ct))
    tpm <- rep(0, length(gene_counts))
  } else {
    tpm <- log10(gene_counts / g_tot * 1e6 + 1)
  }
  rna <- data.frame(gene_name = gene_names, TPM = as.numeric(tpm))
  rna <- rna[order(rna$gene_name), , drop = FALSE]
  rna_path <- file.path(out_dir, paste0(ct_san, ".rna.csv"))
  write.csv(rna, rna_path, row.names = FALSE, quote = FALSE)

  cat(sprintf("[write] %-28s : %4d cells  peaks=%d genes=%d  ->  %s, %s\n",
              ct, n_cells, nrow(bed), nrow(rna),
              basename(atac_path), basename(rna_path)))
  kept_cts <- c(kept_cts, ct_san)
}

# Write the list of cell type keys used in the zarr build / yaml.
writeLines(kept_cts,
           con = file.path(out_dir, "celltypes.txt"))
cat("[done] kept cell types (", length(kept_cts), "):\n",
    paste(kept_cts, collapse = ","), "\n", sep = "")
