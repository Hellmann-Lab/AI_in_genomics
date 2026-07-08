#!/usr/bin/env python3
"""
Build a GET region zarr from preprocessed per-celltype ATAC/RNA files.

Inputs are controlled by environment variables so the same utility can be used
for the human course data or a custom assembly such as macFas6.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(os.environ.get("GET_REPO", Path(__file__).resolve().parents[1])).resolve()
TUTORIAL_DIR = (REPO_ROOT / "tutorials").resolve()
os.chdir(TUTORIAL_DIR)
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TUTORIAL_DIR))

from get_model.dataset.custom_gtf import add_exp_from_gtf  # noqa: E402
from preprocess_utils import (  # noqa: E402
    add_atpm,
    add_exp,
    create_peak_motif,
    get_motif,
    query_motif,
)


COURSE_DATA = Path(os.environ.get("GET_COURSE_DATA", Path.home() / "data" / "GET_course_data"))
COURSE_WORK = Path(os.environ.get("GET_COURSE_WORK", Path.home() / "GET_course_work"))

PREPROC_DIR = Path(
    os.environ.get(
        "GET_PREPROCESSED_DIR",
        COURSE_WORK / "multiome_1" / "preprocessed",
    )
)
MOTIF_BED = Path(
    os.environ.get(
        "GET_MOTIF_BED",
        COURSE_DATA / "annotations" / "hg38.archetype_motifs.v1.0.bed.gz",
    )
)
ZARR_OUT = Path(os.environ.get("GET_MULTIOME_ZARR", PREPROC_DIR / "multiome1_human.zarr"))
GTF_PATH = os.environ.get("GET_GTF", "")
ASSEMBLY = os.environ.get("GET_ASSEMBLY", "hg38")
GENCODE_VERSION = os.environ.get("GET_GENCODE_VERSION", "40")
PROMOTER_EXTEND_BP = int(os.environ.get("GET_PROMOTER_EXTEND_BP", "300"))
GTF_ID_OR_NAME = os.environ.get("GET_GTF_ID_OR_NAME", "gene_name")

STAGING_DIR = Path(os.environ.get("GET_MOTIF_STAGING_DIR", PREPROC_DIR / "_motif_staging"))


def read_celltypes() -> list[str]:
    ct_file = PREPROC_DIR / "celltypes.txt"
    if ct_file.exists():
        cts = [line.strip() for line in ct_file.read_text().splitlines() if line.strip()]
    else:
        cts = sorted(path.stem.split(".")[0] for path in PREPROC_DIR.glob("*.atac.bed"))
    if not cts:
        raise RuntimeError(f"No cell types found in {PREPROC_DIR}")
    return cts


def add_expression(zarr_out: Path, rna: Path, bed: Path, celltype: str) -> None:
    if GTF_PATH:
        add_exp_from_gtf(
            str(zarr_out),
            str(rna),
            str(bed),
            celltype,
            gtf_path=GTF_PATH,
            extend_bp=PROMOTER_EXTEND_BP,
            id_or_name=GTF_ID_OR_NAME,
        )
    else:
        add_exp(
            str(zarr_out),
            str(rna),
            str(bed),
            celltype,
            assembly=ASSEMBLY,
            version=GENCODE_VERSION,
            extend_bp=PROMOTER_EXTEND_BP,
            id_or_name=GTF_ID_OR_NAME,
        )


def main():
    assert MOTIF_BED.exists(), f"missing motif bed: {MOTIF_BED}"
    assert (TUTORIAL_DIR / "human_motif_cluster_id").exists(), (
        "human_motif_cluster_id missing in tutorials dir"
    )
    if GTF_PATH:
        assert Path(GTF_PATH).exists(), f"missing custom GTF: {GTF_PATH}"

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    celltypes = read_celltypes()
    print(f"[build] cell types ({len(celltypes)}): {celltypes}")
    print(f"[build] motif bed: {MOTIF_BED}")
    print(f"[build] expression annotation: {GTF_PATH if GTF_PATH else ASSEMBLY}")

    shared_ct = celltypes[0]
    shared_bed = PREPROC_DIR / f"{shared_ct}.atac.bed"
    print(f"[build] using shared peak bed: {shared_bed}")

    cwd_before = os.getcwd()
    os.chdir(STAGING_DIR)
    try:
        peaks_motif = query_motif(str(shared_bed), str(MOTIF_BED))
        motif_out = get_motif(str(shared_bed), peaks_motif, assembly=ASSEMBLY)

        if ZARR_OUT.exists():
            shutil.rmtree(ZARR_OUT)
        hmci = STAGING_DIR / "human_motif_cluster_id"
        if not hmci.exists():
            os.symlink(TUTORIAL_DIR / "human_motif_cluster_id", hmci)

        create_peak_motif(motif_out, str(ZARR_OUT), str(shared_bed), assembly=ASSEMBLY)
    finally:
        os.chdir(cwd_before)

    for ct in celltypes:
        bed = PREPROC_DIR / f"{ct}.atac.bed"
        rna = PREPROC_DIR / f"{ct}.rna.csv"
        assert bed.exists(), f"missing {bed}"
        assert rna.exists(), f"missing {rna}"
        print(f"[build] add_atpm  {ct}")
        add_atpm(str(ZARR_OUT), str(bed), ct)
        print(f"[build] add_exp   {ct}")
        add_expression(ZARR_OUT, rna, bed, ct)

    print(f"[build] done: {ZARR_OUT}")


if __name__ == "__main__":
    main()
