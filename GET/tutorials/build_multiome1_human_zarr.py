#!/usr/bin/env python3
"""
Build `multiome1_human.zarr` from the per-celltype `.atac.bed` / `.rna.csv`
files written by `prepare_multiome1_human.R`.

Mirrors the end of `prepare_pbmc.ipynb`:
    query_motif -> get_motif -> create_peak_motif -> add_atpm -> add_exp

Run inside the apptainer container using the container's own site-packages
(the user-site `~/.local` can ship incompatible torch/zarr versions):

    bash scripts/course_02_build_zarr.sh
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# preprocess_utils.py reads ./human_motif_cluster_id relative to CWD.
REPO_ROOT = Path(os.environ.get("GET_REPO", Path(__file__).resolve().parents[1])).resolve()
TUTORIAL_DIR = (REPO_ROOT / "tutorials").resolve()
os.chdir(TUTORIAL_DIR)
sys.path.insert(0, str(TUTORIAL_DIR))

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

STAGING_DIR = PREPROC_DIR / "_motif_staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)


def read_celltypes() -> list[str]:
    ct_file = PREPROC_DIR / "celltypes.txt"
    if ct_file.exists():
        cts = [l.strip() for l in ct_file.read_text().splitlines() if l.strip()]
    else:
        cts = sorted(p.stem.split(".")[0] for p in PREPROC_DIR.glob("*.atac.bed"))
    if not cts:
        raise RuntimeError(f"No cell types found in {PREPROC_DIR}")
    return cts


def main():
    assert MOTIF_BED.exists(), f"missing motif bed: {MOTIF_BED}"
    assert (TUTORIAL_DIR / "human_motif_cluster_id").exists(), (
        "human_motif_cluster_id missing in tutorials dir"
    )

    celltypes = read_celltypes()
    print(f"[build] cell types ({len(celltypes)}): {celltypes}")

    shared_ct = celltypes[0]
    shared_bed = PREPROC_DIR / f"{shared_ct}.atac.bed"
    print(f"[build] using shared peak bed: {shared_bed}")

    cwd_before = os.getcwd()
    os.chdir(STAGING_DIR)
    try:
        peaks_motif = query_motif(str(shared_bed), str(MOTIF_BED))
        motif_out = get_motif(str(shared_bed), peaks_motif)

        if ZARR_OUT.exists():
            shutil.rmtree(ZARR_OUT)
        hmci = STAGING_DIR / "human_motif_cluster_id"
        if not hmci.exists():
            os.symlink(TUTORIAL_DIR / "human_motif_cluster_id", hmci)

        create_peak_motif(motif_out, str(ZARR_OUT), str(shared_bed))
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
        add_exp(
            str(ZARR_OUT),
            str(rna),
            str(bed),
            ct,
            assembly="hg38",
            version="40",
            extend_bp=300,
            id_or_name="gene_name",
        )

    print(f"[build] done: {ZARR_OUT}")


if __name__ == "__main__":
    main()
