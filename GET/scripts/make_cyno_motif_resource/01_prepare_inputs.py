#!/usr/bin/env python3
from __future__ import annotations

import gzip
import os
import re
from pathlib import Path


def env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return Path(value)


def parse_fasta_sizes(path: Path) -> list[tuple[str, int]]:
    sizes: list[tuple[str, int]] = []
    name: str | None = None
    length = 0
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    sizes.append((name, length))
                name = line[1:].split()[0]
                length = 0
            else:
                length += len(line.strip())
    if name is not None:
        sizes.append((name, length))
    return sizes


def parse_gtf_contigs(path: Path) -> set[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    contigs: set[str] = set()
    with opener(path, "rt") as handle:
        for line in handle:
            if not line or line.startswith("#"):
                continue
            contigs.add(line.split("\t", 1)[0])
    return contigs


def parse_region(region: str, sizes: dict[str, int]) -> tuple[str, int, int]:
    match = re.fullmatch(r"([^:]+):([0-9,]+)-([0-9,]+)", region)
    if not match:
        raise SystemExit(f"TEST_REGION must look like contig:start-end, got {region!r}")
    contig = match.group(1)
    start_1 = int(match.group(2).replace(",", ""))
    end_1 = int(match.group(3).replace(",", ""))
    if contig not in sizes:
        raise SystemExit(f"TEST_REGION contig {contig!r} is not present in FASTA")
    if start_1 < 1 or end_1 < start_1:
        raise SystemExit(f"invalid TEST_REGION coordinates: {region}")
    start_0 = start_1 - 1
    end_0 = min(end_1, sizes[contig])
    return contig, start_0, end_0


def main() -> None:
    fasta = env_path("GET_CYNO_FASTA")
    gtf = env_path("GET_CYNO_GTF")
    work = env_path("GET_CYNO_WORK_DIR")
    work.mkdir(parents=True, exist_ok=True)

    sizes_list = parse_fasta_sizes(fasta)
    if not sizes_list:
        raise SystemExit(f"no FASTA records found in {fasta}")
    sizes = dict(sizes_list)

    if any(name.startswith("chr") for name, _ in sizes_list[:25]):
        raise SystemExit("FASTA appears to use chr-prefixed contigs; expected Ensembl-style macFas6 names")

    gtf_contigs = parse_gtf_contigs(gtf)
    missing_gtf = sorted(gtf_contigs - set(sizes))
    if missing_gtf:
        raise SystemExit(f"GTF has contigs absent from FASTA, first examples: {missing_gtf[:10]}")

    contigs_tsv = work / "contigs.tsv"
    with contigs_tsv.open("w") as out:
        out.write("rank\tcontig\tsize\n")
        for rank, (contig, size) in enumerate(sizes_list):
            out.write(f"{rank}\t{contig}\t{size}\n")

    test_region = os.environ.get("TEST_REGION")
    scan_regions = work / "scan_regions.tsv"
    with scan_regions.open("w") as out:
        out.write("contig\tstart\tend\tlabel\n")
        if test_region:
            contig, start, end = parse_region(test_region, sizes)
            out.write(f"{contig}\t{start}\t{end}\t{contig}_{start}_{end}\n")
        else:
            for contig, size in sizes_list:
                out.write(f"{contig}\t0\t{size}\t{contig}_0_{size}\n")

    qc = work / "input_qc.md"
    with qc.open("w") as out:
        out.write("# macFas6 motif input QC\n\n")
        out.write(f"- FASTA: `{fasta}`\n")
        out.write(f"- GTF: `{gtf}`\n")
        out.write(f"- FASTA contigs: {len(sizes_list)}\n")
        out.write(f"- GTF contigs: {len(gtf_contigs)}\n")
        out.write(f"- First FASTA contigs: {', '.join(name for name, _ in sizes_list[:10])}\n")
        out.write(f"- TEST_REGION: `{test_region or 'full genome'}`\n")

    print(f"[prepare] wrote {contigs_tsv}")
    print(f"[prepare] wrote {scan_regions}")
    print(f"[prepare] wrote {qc}")


if __name__ == "__main__":
    main()
