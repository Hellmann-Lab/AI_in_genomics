#!/usr/bin/env bash
set -euo pipefail

: "${GET_VIERSTRA_V1_DIR:?GET_VIERSTRA_V1_DIR is required}"
mkdir -p "$GET_VIERSTRA_V1_DIR"

python3 - <<'PY'
from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path
from urllib.request import urlopen

base = "https://resources.altius.org/~jvierstra/projects/motif-clustering"
out_dir = Path(os.environ["GET_VIERSTRA_V1_DIR"])
force = os.environ.get("FORCE", "0") == "1"

files = [
    ("releases/v1.0/motif_annotations.xlsx", "motif_annotations.xlsx", "xlsx"),
    ("releases/v1.0/motif_metadata_v1.0.xlsx", "motif_metadata_v1.0.xlsx", "xlsx"),
    (
        "databases/jaspar2018/JASPAR2018_CORE_vertebrates_non-redundant_pfms.meme",
        "JASPAR2018_CORE_vertebrates_non-redundant_pfms.meme",
        "meme",
    ),
    (
        "databases/hocomoco_v11/HOCOMOCOv11_core_HUMAN_mono_meme_format.meme",
        "HOCOMOCOv11_core_HUMAN_mono_meme_format.meme",
        "meme",
    ),
    (
        "databases/hocomoco_v11/HOCOMOCOv11_core_MOUSE_mono_meme_format.meme",
        "HOCOMOCOv11_core_MOUSE_mono_meme_format.meme",
        "meme",
    ),
]
for idx in range(1, 7):
    files.append((f"databases/jolma2013/table_s3-{idx}.meme", f"jolma2013_table_s3-{idx}.meme", "meme"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(path: Path, kind: str) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"empty download: {path}")
    head = path.read_bytes()[:4096]
    if b"404 Not Found" in head or b"<!DOCTYPE HTML" in head or b"<html" in head.lower():
        raise RuntimeError(f"download looks like an HTML error page: {path}")
    if kind == "meme" and b"MOTIF " not in path.read_bytes():
        raise RuntimeError(f"MEME file contains no MOTIF records: {path}")


manifest_rows = ["path\turl\tbytes\tsha256\ttimestamp_utc"]
for rel_url, name, kind in files:
    url = f"{base}/{rel_url}"
    dest = out_dir / name
    if dest.exists() and not force:
        print(f"[fetch] keep existing {dest}")
    else:
        print(f"[fetch] download {url}")
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        with urlopen(url, timeout=120) as response, tmp.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
        tmp.replace(dest)
    validate(dest, kind)
    manifest_rows.append(
        f"{dest}\t{url}\t{dest.stat().st_size}\t{sha256(dest)}\t{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
    )

(out_dir / "download_manifest.tsv").write_text("\n".join(manifest_rows) + "\n")
print(f"[fetch] wrote {out_dir / 'download_manifest.tsv'}")
PY
