#!/usr/bin/env bash
set -euo pipefail

: "${GET_CYNO_WORK_DIR:?GET_CYNO_WORK_DIR is required}"
: "${GET_CYNO_MOTIF_PREFIX:?GET_CYNO_MOTIF_PREFIX is required}"

COLLAPSED="$GET_CYNO_WORK_DIR/archetype_collapsed.bed"
RANKED="$GET_CYNO_WORK_DIR/archetype_collapsed.ranked.tsv"
SORT_TMP="$GET_CYNO_WORK_DIR/final_sort_tmp"
OUT_BED_GZ="${GET_CYNO_MOTIF_PREFIX}.bed.gz"
QC_MD="${GET_CYNO_MOTIF_PREFIX}.qc.md"

if [[ ! -s "$COLLAPSED" ]]; then
  echo "[finalize] missing collapsed BED: $COLLAPSED" >&2
  exit 1
fi

mkdir -p "$SORT_TMP" "$(dirname "$OUT_BED_GZ")"

python3 - "$GET_CYNO_WORK_DIR/contigs.tsv" "$COLLAPSED" "$RANKED" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

contigs = Path(sys.argv[1])
collapsed = Path(sys.argv[2])
ranked = Path(sys.argv[3])

rank = {}
with contigs.open() as handle:
    next(handle)
    for line in handle:
        rank_s, contig, _size = line.rstrip("\n").split("\t")
        rank[contig] = int(rank_s)

with collapsed.open() as src, ranked.open("w") as out:
    for raw in src:
        fields = raw.rstrip("\n").split("\t")
        if len(fields) != 8:
            raise SystemExit(f"bad collapsed row with {len(fields)} columns: {raw[:200]}")
        contig = fields[0]
        if contig not in rank:
            raise SystemExit(f"contig absent from contig order: {contig}")
        out.write(f"{rank[contig]}\t" + "\t".join(fields) + "\n")
PY

echo "[finalize] sort, bgzip, tabix"
sort --parallel "${THREADS:-8}" -S "${SORT_MEM:-16G}" -T "$SORT_TMP" \
  -k1,1n -k3,3n -k4,4n -k5,5 -k7,7 "$RANKED" \
  | cut -f2- \
  | bgzip -c > "$OUT_BED_GZ"
tabix -f -p bed "$OUT_BED_GZ"

python3 - "$OUT_BED_GZ" "$QC_MD" "$GET_CYNO_WORK_DIR/contigs.tsv" "$PWD/tutorials/human_motif_cluster_id" <<'PY'
from __future__ import annotations

import gzip
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

bed = Path(sys.argv[1])
qc = Path(sys.argv[2])
contigs_tsv = Path(sys.argv[3])
human_ids = Path(sys.argv[4])

contig_sizes = {}
with contigs_tsv.open() as handle:
    next(handle)
    for line in handle:
        _rank, contig, size = line.rstrip("\n").split("\t")
        contig_sizes[contig] = int(size)

human_motifs = {line.strip() for line in human_ids.read_text().splitlines() if line.strip()}
rows = 0
bad_rows = 0
chr_prefixed = 0
clusters = set()
by_contig = Counter()
examples = []

with gzip.open(bed, "rt") as handle:
    for raw in handle:
        rows += 1
        fields = raw.rstrip("\n").split("\t")
        if len(fields) != 8:
            bad_rows += 1
            continue
        contig, start_s, end_s, cluster, score_s, strand, best_model, num_models = fields
        if contig.startswith("chr"):
            chr_prefixed += 1
        try:
            start = int(start_s)
            end = int(end_s)
            float(score_s)
            int(num_models)
            if start < 0 or end <= start or end > contig_sizes.get(contig, -1) or strand not in {"+", "-"}:
                bad_rows += 1
        except ValueError:
            bad_rows += 1
        clusters.add(cluster)
        by_contig[contig] += 1
        if len(examples) < 5:
            examples.append(raw.rstrip("\n"))

missing_for_get = sorted(human_motifs - clusters)
extra_vs_get = sorted(clusters - human_motifs)

smoke_region = os.environ.get("QC_SMOKE_REGION") or os.environ.get("TEST_REGION") or "1:100000-200000"
try:
    smoke = subprocess.run(["tabix", str(bed), smoke_region], check=False, capture_output=True, text=True)
    smoke_lines = [line for line in smoke.stdout.splitlines() if line]
except Exception as exc:
    smoke_lines = [f"tabix failed: {exc}"]

with qc.open("w") as out:
    out.write("# macFas6 archetype motif resource QC\n\n")
    out.write(f"- BED: `{bed}`\n")
    out.write(f"- Index: `{bed}.tbi`\n")
    out.write(f"- Rows: {rows}\n")
    out.write(f"- Bad rows: {bad_rows}\n")
    out.write(f"- chr-prefixed rows: {chr_prefixed}\n")
    out.write(f"- Motif clusters observed: {len(clusters)}\n")
    out.write(f"- GET motif clusters expected: {len(human_motifs)}\n")
    out.write(f"- GET motif clusters missing: {len(missing_for_get)}\n")
    out.write(f"- Extra clusters vs GET order: {len(extra_vs_get)}\n")
    out.write(f"- Smoke region: `{smoke_region}`\n")
    out.write(f"- Smoke rows: {len(smoke_lines)}\n\n")
    if missing_for_get:
        out.write("## Missing GET Motifs\n\n")
        out.write(", ".join(missing_for_get[:200]) + "\n\n")
    out.write("## Top Contigs\n\n")
    for contig, count in by_contig.most_common(25):
        out.write(f"- `{contig}`: {count}\n")
    out.write("\n## Example Rows\n\n")
    out.write("```text\n")
    for row in examples:
        out.write(row + "\n")
    out.write("```\n\n")
    out.write("## Smoke Query Rows\n\n")
    out.write("```text\n")
    for row in smoke_lines[:10]:
        out.write(row + "\n")
    out.write("```\n")

print(f"[finalize] wrote {qc}")
PY

rm -f "$RANKED"
rm -rf "$SORT_TMP"
echo "[finalize] wrote $OUT_BED_GZ"
