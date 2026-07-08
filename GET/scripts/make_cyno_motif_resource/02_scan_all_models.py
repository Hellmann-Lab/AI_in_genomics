#!/usr/bin/env python3
from __future__ import annotations

import gzip
import math
import os
import shutil
from pathlib import Path
from typing import Iterable

import MOODS.scan
import MOODS.tools
import pandas as pd


BG = [float(x) for x in os.environ.get("MOODS_BG", "0.2977,0.2023,0.2023,0.2977").replace(" ", "").split(",")]
PVALUE = float(os.environ.get("MOODS_PVALUE", "0.0001"))
MOTIF_BATCH_SIZE = int(os.environ.get("MOTIF_BATCH_SIZE", "64"))
SCAN_CHUNK_BP = int(os.environ.get("SCAN_CHUNK_BP", "10000000"))
PSEUDOCOUNT = float(os.environ.get("MOODS_PSEUDOCOUNT", "0.001"))
FORCE = os.environ.get("FORCE", "0") == "1"


def env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return Path(value)


def parse_meme(path: Path) -> dict[str, list[list[float]]]:
    motifs: dict[str, list[list[float]]] = {}
    current_name: str | None = None
    rows_left = 0
    rows: list[list[float]] = []
    with path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("MOTIF "):
                if current_name and rows:
                    motifs[current_name] = rows_to_moods_matrix(rows)
                parts = line.split()
                current_name = parts[1]
                rows = []
                rows_left = 0
            elif current_name and line.startswith("letter-probability matrix"):
                width = None
                for part in line.replace("=", " = ").split():
                    if part.isdigit():
                        width = int(part)
                if " w=" in line:
                    after = line.split("w=", 1)[1].split()[0]
                    width = int(after)
                if width is None:
                    raise RuntimeError(f"could not parse motif width in {path}: {line}")
                rows_left = width
            elif current_name and rows_left:
                vals = [float(x) for x in line.split()[:4]]
                if len(vals) != 4:
                    raise RuntimeError(f"bad probability row in {path}: {line}")
                total = sum(vals)
                if total <= 0:
                    vals = [0.25, 0.25, 0.25, 0.25]
                else:
                    vals = [v / total for v in vals]
                rows.append(vals)
                rows_left -= 1
    if current_name and rows:
        motifs[current_name] = rows_to_moods_matrix(rows)
    return motifs


def rows_to_moods_matrix(rows: list[list[float]]) -> list[list[float]]:
    # MEME rows are positions with A C G T columns; MOODS expects one row per base.
    return [[row[i] for row in rows] for i in range(4)]


def load_motifs(vierstra_dir: Path, required: set[str]) -> dict[str, list[list[float]]]:
    motif_files = sorted(vierstra_dir.glob("*.meme"))
    if not motif_files:
        raise SystemExit(f"no MEME files found in {vierstra_dir}; run 00_fetch first")
    motifs: dict[str, list[list[float]]] = {}
    for path in motif_files:
        parsed = parse_meme(path)
        overlap = set(parsed) & set(motifs)
        if overlap:
            raise SystemExit(f"duplicate motif names across MEME files, examples: {sorted(overlap)[:5]}")
        motifs.update(parsed)
    missing = sorted(required - set(motifs))
    if missing:
        raise SystemExit(f"MEME files are missing {len(missing)} metadata motifs, examples: {missing[:20]}")
    return {name: motifs[name] for name in sorted(required)}


def load_required_motifs(vierstra_dir: Path) -> set[str]:
    xlsx = vierstra_dir / "motif_metadata_v1.0.xlsx"
    if not xlsx.exists():
        raise SystemExit(f"missing Vierstra metadata: {xlsx}")
    motifs = pd.read_excel(xlsx, sheet_name="Motifs")
    return set(motifs["Motif"].astype(str))


def load_regions(work: Path) -> list[tuple[str, int, int, str]]:
    regions = []
    with (work / "scan_regions.tsv").open() as handle:
        next(handle)
        for line in handle:
            contig, start, end, label = line.rstrip("\n").split("\t")
            regions.append((contig, int(start), int(end), label))
    return regions


def iter_fasta_records(path: Path) -> Iterable[tuple[str, str]]:
    name: str | None = None
    chunks: list[str] = []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                if name is not None:
                    yield name, "".join(chunks).upper()
                name = line[1:].split()[0]
                chunks = []
            else:
                chunks.append(line.strip())
    if name is not None:
        yield name, "".join(chunks).upper()


def build_scanners(motif_names: list[str], matrices: dict[str, list[list[float]]]):
    score_mats = []
    thresholds = []
    scan_index: list[tuple[str, str, int]] = []
    for motif in motif_names:
        mat = matrices[motif]
        score = MOODS.tools.log_odds(mat, BG, PSEUDOCOUNT)
        threshold = MOODS.tools.threshold_from_p(score, BG, PVALUE)
        score_mats.append(score)
        thresholds.append(threshold)
        scan_index.append((motif, "+", len(mat[0])))

        rc = MOODS.tools.reverse_complement(score)
        score_mats.append(rc)
        thresholds.append(threshold)
        scan_index.append((motif, "-", len(mat[0])))
    return score_mats, thresholds, scan_index


def sanitize_label(label: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in label)


def scan_region(
    contig: str,
    region_start: int,
    region_end: int,
    label: str,
    sequence: str,
    motif_names: list[str],
    matrices: dict[str, list[list[float]]],
    out_dir: Path,
) -> list[Path]:
    output_paths: list[Path] = []
    safe_label = sanitize_label(label)
    max_width = max(len(matrices[name][0]) for name in motif_names)
    overlap = max_width - 1
    n_batches = math.ceil(len(motif_names) / MOTIF_BATCH_SIZE)
    for batch_i in range(n_batches):
        names = motif_names[batch_i * MOTIF_BATCH_SIZE : (batch_i + 1) * MOTIF_BATCH_SIZE]
        out_path = out_dir / f"{safe_label}.batch_{batch_i:05d}.bed.gz"
        output_paths.append(out_path)
        if out_path.exists() and not FORCE:
            print(f"[scan] keep existing {out_path}")
            continue
        score_mats, thresholds, scan_index = build_scanners(names, matrices)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        with gzip.open(tmp, "wt") as out:
            core_start = region_start
            while core_start < region_end:
                core_end = min(core_start + SCAN_CHUNK_BP, region_end)
                chunk_start = max(region_start, core_start - overlap)
                chunk_end = min(region_end, core_end + overlap)
                seq = sequence[chunk_start:chunk_end]
                if seq:
                    matches = MOODS.scan.scan_dna(seq, score_mats, BG, thresholds)
                    for matrix_i, motif_matches in enumerate(matches):
                        motif, strand, width = scan_index[matrix_i]
                        for match in motif_matches:
                            start = chunk_start + int(match.pos)
                            end = start + width
                            if start < core_start or start >= core_end or end > region_end:
                                continue
                            hit_seq = sequence[start:end]
                            if "N" in hit_seq:
                                continue
                            out.write(
                                f"{contig}\t{start}\t{end}\t{motif}\t{float(match.score):.10f}\t{strand}\t{hit_seq}\n"
                            )
                core_start = core_end
        tmp.replace(out_path)
        print(f"[scan] wrote {out_path}")
    return output_paths


def main() -> None:
    fasta = env_path("GET_CYNO_FASTA")
    work = env_path("GET_CYNO_WORK_DIR")
    vierstra = env_path("GET_VIERSTRA_V1_DIR")
    scan_dir = work / "full_model_scans"
    if FORCE and scan_dir.exists():
        shutil.rmtree(scan_dir)
    scan_dir.mkdir(parents=True, exist_ok=True)

    required = load_required_motifs(vierstra)
    matrices = load_motifs(vierstra, required)
    motif_names = sorted(matrices)
    regions = load_regions(work)
    regions_by_contig: dict[str, list[tuple[int, int, str]]] = {}
    for contig, start, end, label in regions:
        regions_by_contig.setdefault(contig, []).append((start, end, label))

    manifest = scan_dir / "scan_manifest.tsv"
    manifest_rows = ["path\tcontig\tstart\tend\tlabel"]
    for contig, seq in iter_fasta_records(fasta):
        if contig not in regions_by_contig:
            continue
        for start, end, label in regions_by_contig[contig]:
            print(f"[scan] contig={contig} start={start} end={end} motifs={len(motif_names)}")
            paths = scan_region(contig, start, end, label, seq, motif_names, matrices, scan_dir)
            for path in paths:
                manifest_rows.append(f"{path}\t{contig}\t{start}\t{end}\t{label}")
    manifest.write_text("\n".join(manifest_rows) + "\n")
    print(f"[scan] wrote {manifest}")


if __name__ == "__main__":
    main()
