import gzip
import re
from pathlib import Path

import numpy as np
import pandas as pd
import zarr
from pyranges import PyRanges as pr


_ATTR_RE = re.compile(r'([A-Za-z0-9_.-]+) "([^"]*)"')


class CustomGTF:
    """Small Gencode-like wrapper for course genomes with local GTF files."""

    def __init__(self, assembly: str, gtf_path: str):
        self.assembly = assembly
        self.gtf_path = Path(gtf_path)
        if not self.gtf_path.exists():
            raise FileNotFoundError(f"Custom GTF does not exist: {self.gtf_path}")
        self.gtf = read_tss_gtf(self.gtf_path)


def _open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt")
    return path.open("rt")


def _parse_attributes(value: str) -> dict[str, str]:
    return {key: val for key, val in _ATTR_RE.findall(value)}


def read_tss_gtf(gtf_path: str | Path) -> pd.DataFrame:
    """Read gene rows from a GTF and return TSS points in Gencode-like columns."""
    rows = []
    gtf_path = Path(gtf_path)
    with _open_text(gtf_path) as handle:
        for raw in handle:
            if not raw or raw.startswith("#"):
                continue
            fields = raw.rstrip("\n").split("\t")
            if len(fields) < 9 or fields[2] != "gene":
                continue

            chrom, _, _, start, end, _, strand, _, attrs = fields
            parsed = _parse_attributes(attrs)
            gene_id = parsed.get("gene_id")
            gene_name = parsed.get("gene_name", gene_id)
            if not gene_id or not gene_name or strand not in {"+", "-"}:
                continue

            start_i = int(start)
            end_i = int(end)
            # GTF is 1-based closed; BED/PyRanges are 0-based half-open.
            tss = start_i - 1 if strand == "+" else end_i
            rows.append(
                {
                    "Chromosome": chrom,
                    "Start": tss,
                    "End": tss,
                    "Strand": strand,
                    "gene_name": gene_name,
                    "gene_id": gene_id.split(".")[0],
                    "gene_type": parsed.get("gene_type", parsed.get("gene_biotype", "")),
                    "transcript_id": parsed.get("transcript_id", gene_id),
                }
            )

    if not rows:
        raise ValueError(f"No gene features with gene_id/gene_name found in {gtf_path}")

    gtf = pd.DataFrame(rows)
    gtf.insert(0, "index", np.arange(len(gtf), dtype=np.int64))
    gtf["chrom_count"] = gtf.groupby("Chromosome")["Chromosome"].transform("count")
    return gtf[
        [
            "index",
            "Chromosome",
            "Start",
            "End",
            "Strand",
            "gene_name",
            "gene_id",
            "gene_type",
            "transcript_id",
            "chrom_count",
        ]
    ]


def _replace_zarr_dataset(zroot, name: str, data):
    if name in zroot:
        del zroot[name]
    zroot.create_dataset(name, data=data)


def add_exp_from_gtf(
    zarr_file: str,
    rna_file: str,
    atac_file: str,
    celltype: str,
    gtf_path: str,
    extend_bp: int = 300,
    id_or_name: str = "gene_name",
) -> None:
    """Add expression/TSS arrays to a zarr using a local GTF instead of Gencode."""
    gtf = read_tss_gtf(gtf_path)
    gene_exp = pd.read_csv(rna_file)
    if id_or_name == "gene_id":
        gene_exp["gene_id"] = gene_exp["gene_id"].astype(str).str.split(".").str[0]
        promoter_exp = pd.merge(gtf, gene_exp, on="gene_id")
    elif id_or_name == "gene_name":
        promoter_exp = pd.merge(gtf, gene_exp, on="gene_name")
    else:
        raise ValueError(f"Invalid GET_GTF_ID_OR_NAME: {id_or_name}")

    atac = pd.read_csv(
        atac_file,
        sep="\t",
        header=None,
        names=["Chromosome", "Start", "End", "aTPM"],
        dtype={"Chromosome": str},
    ).reset_index()

    z = zarr.open(zarr_file, mode="a")
    peak_names = z["peak_names"][:]
    n_peaks = len(peak_names)

    exp_positive = np.zeros(n_peaks, dtype=np.float32)
    exp_negative = np.zeros(n_peaks, dtype=np.float32)
    tss = np.zeros((n_peaks, 2), dtype=np.int8)
    gene_idx_rows = []

    if not promoter_exp.empty:
        joined = (
            pr(atac, int64=True)
            .join(pr(promoter_exp, int64=True).extend(extend_bp), how="left")
            .as_df()
        )
        joined["gene_name"] = joined["gene_name"].astype(str)
        joined = joined[
            (joined["index"] >= 0)
            & joined["gene_name"].notna()
            & (joined["gene_name"] != "-1")
            & joined["TPM"].notna()
            & (joined["TPM"] >= 0)
            & joined["Strand"].isin(["+", "-"])
        ].copy()

        if not joined.empty:
            gene_idx_rows = joined[["index", "gene_name", "Strand"]].drop_duplicates()
            grouped = (
                joined[["index", "Strand", "TPM"]]
                .groupby(["index", "Strand"], as_index=False, observed=True)
                .mean()
            )
            for row in grouped.itertuples(index=False):
                peak_idx = int(row.index)
                value = max(float(row.TPM), 0.0)
                if 0 <= peak_idx < n_peaks and row.Strand == "+":
                    exp_positive[peak_idx] = value
                    tss[peak_idx, 0] = 1
                elif 0 <= peak_idx < n_peaks and row.Strand == "-":
                    exp_negative[peak_idx] = value
                    tss[peak_idx, 1] = 1

    for group in ["expression_positive", "expression_negative", "tss"]:
        if group not in z:
            z.create_group(group)

    z["expression_positive"].create_dataset(
        celltype,
        data=exp_positive,
        overwrite=True,
        chunks=(1000,),
        dtype=np.float32,
    )
    z["expression_negative"].create_dataset(
        celltype,
        data=exp_negative,
        overwrite=True,
        chunks=(1000,),
        dtype=np.float32,
    )
    z["tss"].create_dataset(
        celltype,
        data=tss,
        overwrite=True,
        chunks=(1000, 2),
        dtype=np.int8,
    )

    if len(gene_idx_rows) == 0:
        gene_idx_index = np.array([], dtype=np.int64)
        gene_idx_name = np.array([], dtype="U1")
        gene_idx_strand = np.array([], dtype="U1")
    else:
        gene_idx_index = gene_idx_rows["index"].to_numpy(dtype=np.int64)
        gene_idx_name = gene_idx_rows["gene_name"].astype(str).to_numpy(dtype=str)
        gene_idx_strand = gene_idx_rows["Strand"].astype(str).to_numpy(dtype=str)

    _replace_zarr_dataset(z, "gene_idx_info_index", gene_idx_index)
    _replace_zarr_dataset(z, "gene_idx_info_name", gene_idx_name)
    _replace_zarr_dataset(z, "gene_idx_info_strand", gene_idx_strand)
