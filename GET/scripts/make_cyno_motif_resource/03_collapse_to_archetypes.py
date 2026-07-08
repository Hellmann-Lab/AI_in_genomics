#!/usr/bin/env python3
from __future__ import annotations

import gzip
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd


FORCE = os.environ.get("FORCE", "0") == "1"
KEEP_FULL_SCAN = os.environ.get("KEEP_FULL_SCAN", "0") == "1"
KEEP_ADJUSTED = os.environ.get("KEEP_ADJUSTED", "0") == "1"
THREADS = os.environ.get("THREADS", "8")
SORT_MEM = os.environ.get("SORT_MEM", "16G")


def env_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return Path(value)


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt")
    return path.open()


def load_contig_sizes(work: Path) -> dict[str, int]:
    sizes = {}
    with (work / "contigs.tsv").open() as handle:
        next(handle)
        for line in handle:
            _rank, contig, size = line.rstrip("\n").split("\t")
            sizes[contig] = int(size)
    return sizes


def load_metadata(vierstra: Path) -> dict[str, dict[str, object]]:
    annotations = pd.read_excel(vierstra / "motif_annotations.xlsx", sheet_name=None)
    clusters = annotations["Archetype clusters"].copy()
    motifs = annotations["Motifs"].copy()
    cluster_name = dict(zip(clusters["Cluster_ID"].astype(int), clusters["Name"].astype(str)))
    motif_meta = {}
    for row in motifs.to_dict(orient="records"):
        cid = int(row["Cluster_ID"])
        motif = str(row["Motif"])
        motif_meta[motif] = {
            "cluster": cluster_name[cid],
            "rel": str(row["Relative_orientation"]),
            "left": int(row["Left_offset"]),
            "right": int(row["Right_offset"]),
            "width": int(row["Width"]),
        }
    return motif_meta


def opposite(strand: str) -> str:
    return "-" if strand == "+" else "+"


def adjust_row(fields: list[str], meta: dict[str, object], contig_sizes: dict[str, int]) -> str | None:
    contig = fields[0]
    start = int(fields[1])
    end = int(fields[2])
    motif = fields[3]
    score = fields[4]
    strand = fields[5]
    rel = meta["rel"]
    left = int(meta["left"])
    right = int(meta["right"])
    cluster = str(meta["cluster"])
    archetype_strand = strand if rel == "+" else opposite(strand)
    if archetype_strand == "+":
        adj_start = start - left
        adj_end = end + right
    else:
        adj_start = start - right
        adj_end = end + left
    if adj_start < 0 or adj_end > contig_sizes.get(contig, -1) or adj_start >= adj_end:
        return None
    return f"{contig}\t{adj_start}\t{adj_end}\t{cluster}\t{score}\t{archetype_strand}\t{motif}\n"


def collapse_sorted(sorted_path: Path, out_path: Path) -> None:
    current_key: tuple[str, str, str, str, str] | None = None
    best_score = float("-inf")
    best_model = ""
    models: set[str] = set()

    def flush(out):
        if current_key is None:
            return
        contig, start, end, cluster, strand = current_key
        out.write(f"{contig}\t{start}\t{end}\t{cluster}\t{best_score:.4f}\t{strand}\t{best_model}\t{len(models)}\n")

    with sorted_path.open() as handle, out_path.open("w") as out:
        for line in handle:
            contig, start, end, cluster, score_s, strand, model = line.rstrip("\n").split("\t")
            key = (contig, start, end, cluster, strand)
            score = float(score_s)
            if current_key is not None and key != current_key:
                flush(out)
                best_score = float("-inf")
                best_model = ""
                models = set()
            current_key = key
            models.add(model)
            if score > best_score:
                best_score = score
                best_model = model
        flush(out)


def main() -> None:
    work = env_path("GET_CYNO_WORK_DIR")
    vierstra = env_path("GET_VIERSTRA_V1_DIR")
    scan_dir = work / "full_model_scans"
    collapsed = work / "archetype_collapsed.bed"
    adjusted = work / "archetype_adjusted.unsorted.tsv"
    sorted_adjusted = work / "archetype_adjusted.sorted.tsv"
    sort_tmp = work / "sort_tmp"
    sort_tmp.mkdir(parents=True, exist_ok=True)

    if collapsed.exists() and not FORCE:
        print(f"[collapse] keep existing {collapsed}")
        return

    motif_meta = load_metadata(vierstra)
    contig_sizes = load_contig_sizes(work)
    shards = sorted(scan_dir.glob("*.bed.gz")) + sorted(scan_dir.glob("*.bed"))
    if not shards:
        raise SystemExit(f"no scan shards found in {scan_dir}; run 02_scan_all_models.py first")

    with adjusted.open("w") as out:
        skipped_unknown = 0
        skipped_bounds = 0
        for shard in shards:
            print(f"[collapse] adjust {shard}")
            with open_text(shard) as handle:
                for raw in handle:
                    fields = raw.rstrip("\n").split("\t")
                    if len(fields) < 7:
                        continue
                    meta = motif_meta.get(fields[3])
                    if meta is None:
                        skipped_unknown += 1
                        continue
                    adjusted_row = adjust_row(fields, meta, contig_sizes)
                    if adjusted_row is None:
                        skipped_bounds += 1
                        continue
                    out.write(adjusted_row)
    print(f"[collapse] skipped unknown motifs: {skipped_unknown}")
    print(f"[collapse] skipped out-of-bounds archetypes: {skipped_bounds}")

    cmd = [
        "sort",
        "--parallel",
        THREADS,
        "-S",
        SORT_MEM,
        "-T",
        str(sort_tmp),
        "-k1,1",
        "-k2,2n",
        "-k3,3n",
        "-k4,4",
        "-k6,6",
        str(adjusted),
    ]
    print("[collapse] external sort")
    with sorted_adjusted.open("w") as out:
        subprocess.run(cmd, check=True, stdout=out)

    print(f"[collapse] collapse sorted rows -> {collapsed}")
    collapse_sorted(sorted_adjusted, collapsed)

    if not KEEP_ADJUSTED:
        adjusted.unlink(missing_ok=True)
        sorted_adjusted.unlink(missing_ok=True)
        shutil.rmtree(sort_tmp, ignore_errors=True)
    if not KEEP_FULL_SCAN:
        for shard in shards:
            shard.unlink(missing_ok=True)
    print(f"[collapse] wrote {collapsed}")


if __name__ == "__main__":
    main()
