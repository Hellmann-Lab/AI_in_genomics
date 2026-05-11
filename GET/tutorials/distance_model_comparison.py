"""Compare GET's learned TSS-CRE attributions against simple distance models.

Inputs
------
- interpret_ft_hepatocytes/hepatocytes.zarr  (fine-tuned LoRA inference)
- input_data/multiome_1/preprocessed/multiome1_human.zarr (motif names)

Per (sample, region) we extract:
    d_genomic  signed genomic distance between region midpoint and TSS midpoint (bp)
    d_gene     signed distance in gene orientation (5'->3' positive)
    a          accessibility (ATPM channel of input)
    g_abs      |sum over 282 motif channels of J[r,m] * x[r,m]|  (motif-only, no accessibility)

Framings
--------
A  Explain GET's learned weights:
     for each candidate weighting w(d; theta), per-gene Spearman(w, g_abs).
B  ABC-style expression benchmark:
     per-gene predicted exp = max over sample(s) of  sum_r w_r(d; theta) * a_r,
     compared with observed TSS expression.
C  Accessibility-gated repeats of A and B.

Outputs under
    $GET_COURSE_WORK/output/finetune_multiome1_human/distance_model_comparison/
"""

from __future__ import annotations

import json
import os
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import zarr
from scipy.stats import pearsonr, spearmanr

warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_context("notebook")
sns.set_style("whitegrid")

COURSE_WORK = Path(os.environ.get("GET_COURSE_WORK", Path.home() / "GET_course_work"))
OUT_ROOT = COURSE_WORK / "output" / "finetune_multiome1_human"
FT_ZARR = Path(os.environ.get("GET_FT_INTERPRET_ZARR", OUT_ROOT / "interpret_ft_hepatocytes" / "hepatocytes.zarr"))
OUT_DIR = Path(os.environ.get("GET_DISTANCE_OUT_DIR", OUT_ROOT / "distance_model_comparison"))
OUT_DIR.mkdir(parents=True, exist_ok=True)
print("Output dir:", OUT_DIR)


# ---------------------------------------------------------------------------
# 1) Build per-(sample, region) long table
# ---------------------------------------------------------------------------


def build_long_table(zarr_path: Path, chunk: int = 512) -> pd.DataFrame:
    """Stream through the interpret zarr once and materialise the long table.

    The motif importance is computed as the strand-picked jacobian times the
    model input, summed over the 282 motif channels only (accessibility
    excluded as per the analysis spec).
    """
    z = zarr.open(str(zarr_path), mode="r")
    genes = np.array([g.strip() for g in z["available_genes"][:]])
    chroms = np.array([c.strip() for c in z["chromosome"][:]])
    strands = z["strand"][:].astype(np.int64)
    focus = z["focus"][:]
    peak_coord = z["peak_coord"][:]  # (N, 200, 2)

    j0 = z["jacobians/exp/0/input/region_motif"]
    j1 = z["jacobians/exp/1/input/region_motif"]
    inp = z["input"]
    obs = z["obs/exp"][:]
    preds = z["preds/exp"][:]

    n = genes.shape[0]
    n_regions = peak_coord.shape[1]
    n_motifs = 282

    # per-sample scalars captured for framing B
    tss_idx_main = np.full(n, -1, dtype=np.int64)
    tss_mid = np.zeros(n, dtype=np.float64)
    a_tss = np.zeros(n, dtype=np.float32)
    obs_tss = np.zeros(n, dtype=np.float32)
    pred_tss = np.zeros(n, dtype=np.float32)
    n_tss_peaks = np.zeros(n, dtype=np.int64)

    region_mids = 0.5 * (peak_coord[..., 0] + peak_coord[..., 1])  # (N, 200)

    # storage for the long arrays (written in chunks to stay memory-cheap)
    d_gen = np.zeros(n * n_regions, dtype=np.float32)
    a_all = np.zeros(n * n_regions, dtype=np.float32)
    g_abs = np.zeros(n * n_regions, dtype=np.float32)
    is_tss = np.zeros(n * n_regions, dtype=bool)
    sample_idx_col = np.repeat(np.arange(n), n_regions).astype(np.int32)
    region_idx_col = np.tile(np.arange(n_regions), n).astype(np.int16)

    t0 = time.time()
    for start in range(0, n, chunk):
        end = min(start + chunk, n)
        k = end - start

        s = strands[start:end]
        f = focus[start:end]
        mids = region_mids[start:end]  # (k, 200)

        j0_c = j0[start:end]  # (k, 200, 283) float32
        j1_c = j1[start:end]
        inp_c = inp[start:end].astype(np.float32)

        picked = np.where(s[:, None, None] == 0, j0_c, j1_c)
        contrib_motif = (picked[..., :n_motifs] * inp_c[..., :n_motifs]).sum(axis=-1)  # (k, 200)
        g_abs_c = np.abs(contrib_motif)
        a_c = inp_c[..., -1]  # (k, 200)

        for jj in range(k):
            i = start + jj
            tss_peaks = f[jj][f[jj] >= 0].astype(np.int64)
            n_tss_peaks[i] = len(tss_peaks)
            if len(tss_peaks) == 0:
                tss_idx_main[i] = -1
                tss_mid[i] = np.nan
                continue
            tss_idx_main[i] = int(tss_peaks[0])
            tss_mid[i] = float(mids[jj, tss_peaks].mean())
            a_tss[i] = float(a_c[jj, tss_peaks].max())
            obs_tss[i] = float(obs[i, tss_peaks, s[jj]].max())
            pred_tss[i] = float(preds[i, tss_peaks, s[jj]].max())

            mask = np.zeros(n_regions, dtype=bool)
            mask[tss_peaks] = True
            slot = slice(i * n_regions, (i + 1) * n_regions)
            is_tss[slot] = mask
            d_gen[slot] = mids[jj] - tss_mid[i]
            a_all[slot] = a_c[jj]
            g_abs[slot] = g_abs_c[jj]

        if (start // chunk) % 5 == 0:
            dt = time.time() - t0
            print(f"  chunk {start:5d}/{n}  elapsed {dt:6.1f}s")

    # strand sign -> gene-oriented distance (strand 0 assumed plus; strand 1 minus).
    strand_sign = np.where(strands == 0, 1, -1).astype(np.int32)
    d_gene = d_gen * strand_sign[sample_idx_col]

    df = pd.DataFrame(
        {
            "sample_idx": sample_idx_col,
            "region_idx": region_idx_col,
            "d_genomic": d_gen,
            "d_gene": d_gene.astype(np.float32),
            "a": a_all,
            "g_abs": g_abs,
            "is_tss": is_tss,
        }
    )
    # drop samples with no TSS peak (shouldn't happen per earlier diagnostic)
    valid_samples = tss_idx_main >= 0
    df = df[valid_samples[df["sample_idx"].to_numpy()]].reset_index(drop=True)

    meta = pd.DataFrame(
        {
            "sample_idx": np.arange(n),
            "gene": genes,
            "chrom": chroms,
            "strand": strands.astype(np.int8),
            "tss_idx": tss_idx_main,
            "tss_mid": tss_mid,
            "a_tss": a_tss,
            "obs_tss": obs_tss,
            "pred_tss_GET": pred_tss,
            "n_tss_peaks": n_tss_peaks,
        }
    )
    meta = meta[valid_samples].reset_index(drop=True)
    return df, meta


print("Loading ft interpret zarr and streaming long table ...")
long_df, meta_df = build_long_table(FT_ZARR)
print("long_df:", long_df.shape, " meta_df:", meta_df.shape)

long_path = OUT_DIR / "per_region_long.parquet"
long_df.to_parquet(long_path, index=False)
meta_df.to_parquet(OUT_DIR / "per_sample_meta.parquet", index=False)
print("wrote", long_path)


# ---------------------------------------------------------------------------
# 2) Empirical decay curves
# ---------------------------------------------------------------------------

abs_d = np.abs(long_df["d_genomic"].to_numpy())
g = long_df["g_abs"].to_numpy()
a = long_df["a"].to_numpy()

# log-spaced bins from 100 bp to 10 Mb, plus an explicit TSS (|d|==0) bin
log_bins = np.concatenate([[0], np.logspace(np.log10(200), np.log10(5e6), 30)])
bin_idx = np.digitize(abs_d, log_bins) - 1
bin_idx = np.clip(bin_idx, 0, len(log_bins) - 2)
bin_centers = 0.5 * (log_bins[:-1] + log_bins[1:])
bin_centers[0] = 100.0  # plot-friendly value for the TSS bin

decay_rows = []
for b in range(len(log_bins) - 1):
    m = bin_idx == b
    if m.sum() < 50:
        continue
    decay_rows.append(
        dict(
            bin_lo=log_bins[b],
            bin_hi=log_bins[b + 1],
            bin_center=bin_centers[b],
            n=int(m.sum()),
            mean_g=float(g[m].mean()),
            median_g=float(np.median(g[m])),
            mean_g_access=float(g[m & (a >= np.median(a))].mean()),
            mean_g_closed=float(g[m & (a < np.median(a))].mean()),
        )
    )
decay_df = pd.DataFrame(decay_rows)
decay_df.to_csv(OUT_DIR / "empirical_decay.csv", index=False)
print("wrote empirical_decay.csv (rows:", len(decay_df), ")")


# ---------------------------------------------------------------------------
# 3) Candidate weighting functions
# ---------------------------------------------------------------------------


def w_tss_only(d, focus):
    return focus.astype(np.float32)


def w_cutoff(d, L):
    return (np.abs(d) <= L).astype(np.float32)


def w_linear(d, L):
    return np.clip(1.0 - np.abs(d) / L, 0.0, None).astype(np.float32)


def w_exp(d, tau):
    return np.exp(-np.abs(d) / tau).astype(np.float32)


def w_power(d, d0, alpha):
    return (1.0 / (1.0 + np.abs(d) / d0) ** alpha).astype(np.float32)


def w_loginv(d, d0):
    return (1.0 / np.log(np.e + np.abs(d) / d0)).astype(np.float32)


def w_uniform(d):
    return np.ones_like(d, dtype=np.float32)


# (name, fn, kwargs) – kwargs are in bp
MODELS = []
MODELS.append(("tss_only", "tss_only", {}))
MODELS.append(("uniform_200", "uniform", {}))
for L in (2e3, 5e3, 10e3, 20e3, 50e3, 100e3, 500e3, 1e6):
    MODELS.append((f"cutoff_{int(L/1e3)}kb", "cutoff", dict(L=L)))
for L in (10e3, 25e3, 50e3, 100e3, 250e3, 500e3):
    MODELS.append((f"linear_{int(L/1e3)}kb", "linear", dict(L=L)))
for tau in (1e3, 2.5e3, 5e3, 10e3, 25e3, 50e3, 100e3):
    MODELS.append((f"exp_{tau/1e3:g}kb", "exp", dict(tau=tau)))
for d0, alpha in [(1e3, 1), (5e3, 1), (10e3, 1), (1e3, 2), (5e3, 0.5), (10e3, 2)]:
    MODELS.append((f"power_d0{int(d0/1e3)}kb_a{alpha}", "power", dict(d0=d0, alpha=alpha)))
for d0 in (1e3, 5e3, 25e3):
    MODELS.append((f"loginv_d0{int(d0/1e3)}kb", "loginv", dict(d0=d0)))

# top-k is applied per sample below, not via this table
MODEL_FNS = {
    "tss_only": w_tss_only,
    "uniform": lambda d, **_: w_uniform(d),
    "cutoff": lambda d, L: w_cutoff(d, L),
    "linear": lambda d, L: w_linear(d, L),
    "exp": lambda d, tau: w_exp(d, tau),
    "power": lambda d, d0, alpha: w_power(d, d0, alpha),
    "loginv": lambda d, d0: w_loginv(d, d0),
}


# ---------------------------------------------------------------------------
# 4) Framing A: per-gene Spearman(w, g_abs)
# ---------------------------------------------------------------------------

d_signed = long_df["d_genomic"].to_numpy()
focus_col = long_df["is_tss"].to_numpy()
sample_col = long_df["sample_idx"].to_numpy()
# gene per row (for grouping): look up via meta
gene_of_sample = meta_df.set_index("sample_idx")["gene"].to_dict()
gene_col = np.array([gene_of_sample[s] for s in sample_col])


def per_gene_spearman(w: np.ndarray, g_arr: np.ndarray, gene_arr: np.ndarray):
    """Median / mean per-gene Spearman rho. Skips genes where w or g is constant."""
    df = pd.DataFrame({"gene": gene_arr, "w": w, "g": g_arr})
    rhos = []
    for gene, sub in df.groupby("gene", sort=False):
        if sub["w"].nunique() < 2 or sub["g"].nunique() < 2:
            continue
        rho, _ = spearmanr(sub["w"].to_numpy(), sub["g"].to_numpy())
        if np.isfinite(rho):
            rhos.append(rho)
    return float(np.median(rhos)), float(np.mean(rhos)), len(rhos)


A_rows = []
for name, fn_key, kwargs in MODELS:
    if fn_key == "tss_only":
        w = MODEL_FNS[fn_key](d_signed, focus_col)
    else:
        w = MODEL_FNS[fn_key](d_signed, **kwargs)
    med, mean, n_genes = per_gene_spearman(w, g, gene_col)
    pool_rho, _ = spearmanr(w, g)
    A_rows.append(
        dict(
            model=name,
            family=fn_key,
            params=json.dumps(kwargs),
            median_rho=med,
            mean_rho=mean,
            pooled_rho=float(pool_rho),
            n_genes_scored=n_genes,
        )
    )
    print(f"  A  {name:26s}  median rho={med:+.3f}  mean={mean:+.3f}  pooled={pool_rho:+.3f}")

# top-k per sample: evaluated outside the unified loop
for k in (1, 5, 10, 20, 50):
    rhos = []
    pool_w = np.zeros_like(d_signed, dtype=np.float32)
    for samp, grp in long_df.groupby("sample_idx"):
        idx = grp.index.to_numpy()
        dd = grp["d_genomic"].to_numpy()
        kk = min(k, len(dd))
        order = np.argsort(np.abs(dd))[:kk]
        ww = np.zeros(len(dd), dtype=np.float32)
        ww[order] = 1.0
        pool_w[idx] = ww
    med, mean, n_genes = per_gene_spearman(pool_w, g, gene_col)
    pool_rho, _ = spearmanr(pool_w, g)
    A_rows.append(
        dict(
            model=f"topk_{k}",
            family="topk",
            params=json.dumps(dict(k=k)),
            median_rho=med,
            mean_rho=mean,
            pooled_rho=float(pool_rho),
            n_genes_scored=n_genes,
        )
    )
    print(f"  A  topk_{k:<22d}  median rho={med:+.3f}  mean={mean:+.3f}  pooled={pool_rho:+.3f}")

A_df = pd.DataFrame(A_rows).sort_values("median_rho", ascending=False).reset_index(drop=True)
A_df.to_csv(OUT_DIR / "framing_A_leaderboard.csv", index=False)
print("wrote framing_A_leaderboard.csv")


# ---------------------------------------------------------------------------
# 5) Framing B: ABC-style expression prediction
# ---------------------------------------------------------------------------

def model_expression_predictions(w: np.ndarray, a_arr: np.ndarray, sample_arr: np.ndarray, n_samples: int):
    """Aggregate sum_r w_r * a_r per sample. Returns (n_samples,) array of predictions."""
    contrib = w * a_arr
    preds = np.zeros(n_samples, dtype=np.float64)
    np.add.at(preds, sample_arr, contrib)
    return preds


# per-gene aggregation: follow existing convention -> max across the gene's samples.
def per_gene_metrics(sample_pred: np.ndarray, meta: pd.DataFrame):
    df = meta.assign(pred=sample_pred)
    per_gene = df.groupby("gene", as_index=False).agg(
        obs=("obs_tss", "max"),
        pred=("pred", "max"),
    )
    x = per_gene["obs"].to_numpy()
    y = per_gene["pred"].to_numpy()
    mask = np.isfinite(x) & np.isfinite(y) & (np.std(y) > 0)
    if mask.sum() < 10:
        return dict(pearson=np.nan, spearman=np.nan, n=int(mask.sum()))
    r, _ = pearsonr(x[mask], y[mask])
    rho, _ = spearmanr(x[mask], y[mask])
    return dict(pearson=float(r), spearman=float(rho), n=int(mask.sum()))


n_samples = meta_df.shape[0]
B_rows = []

# ceiling: GET itself
get_per_gene = meta_df.groupby("gene", as_index=False).agg(obs=("obs_tss", "max"), pred=("pred_tss_GET", "max"))
r, _ = pearsonr(get_per_gene["obs"], get_per_gene["pred"])
rho, _ = spearmanr(get_per_gene["obs"], get_per_gene["pred"])
B_rows.append(dict(model="GET_finetuned", family="GET", params="{}", pearson=float(r), spearman=float(rho), n=len(get_per_gene)))
print(f"  B  GET_finetuned (ceiling)      pearson={r:+.3f}  spearman={rho:+.3f}")

# floor: a_TSS alone
a_tss_floor = meta_df.groupby("gene", as_index=False).agg(obs=("obs_tss", "max"), pred=("a_tss", "max"))
r, _ = pearsonr(a_tss_floor["obs"], a_tss_floor["pred"])
rho, _ = spearmanr(a_tss_floor["obs"], a_tss_floor["pred"])
B_rows.append(dict(model="a_TSS_only", family="floor", params="{}", pearson=float(r), spearman=float(rho), n=len(a_tss_floor)))
print(f"  B  a_TSS_only (floor)           pearson={r:+.3f}  spearman={rho:+.3f}")

a_arr = long_df["a"].to_numpy()
for name, fn_key, kwargs in MODELS:
    if fn_key == "tss_only":
        w = MODEL_FNS[fn_key](d_signed, focus_col)
    else:
        w = MODEL_FNS[fn_key](d_signed, **kwargs)
    pred_per_sample = model_expression_predictions(w, a_arr, sample_col, n_samples)
    m = per_gene_metrics(pred_per_sample, meta_df)
    B_rows.append(dict(model=name, family=fn_key, params=json.dumps(kwargs), **m))
    print(f"  B  {name:26s}  pearson={m['pearson']:+.3f}  spearman={m['spearman']:+.3f}")

# top-k for framing B
for k in (1, 5, 10, 20, 50):
    pool_w = np.zeros_like(d_signed, dtype=np.float32)
    for samp, grp in long_df.groupby("sample_idx"):
        idx = grp.index.to_numpy()
        dd = grp["d_genomic"].to_numpy()
        kk = min(k, len(dd))
        order = np.argsort(np.abs(dd))[:kk]
        ww = np.zeros(len(dd), dtype=np.float32)
        ww[order] = 1.0
        pool_w[idx] = ww
    pred_per_sample = model_expression_predictions(pool_w, a_arr, sample_col, n_samples)
    m = per_gene_metrics(pred_per_sample, meta_df)
    B_rows.append(dict(model=f"topk_{k}", family="topk", params=json.dumps(dict(k=k)), **m))
    print(f"  B  topk_{k:<22d}  pearson={m['pearson']:+.3f}  spearman={m['spearman']:+.3f}")

B_df = pd.DataFrame(B_rows).sort_values("pearson", ascending=False).reset_index(drop=True)
B_df.to_csv(OUT_DIR / "framing_B_leaderboard.csv", index=False)
print("wrote framing_B_leaderboard.csv")


# ---------------------------------------------------------------------------
# 6) Framing C: accessibility-gated repeats
# ---------------------------------------------------------------------------

q_a_region = float(np.median(a_arr))
q_a_tss = float(np.median(meta_df["a_tss"].to_numpy()))

# Gate 1: restrict to samples where a_TSS > median
samples_open_tss = meta_df.loc[meta_df["a_tss"] > q_a_tss, "sample_idx"].to_numpy()
mask_open_tss_rows = np.isin(sample_col, samples_open_tss)

# Gate 2: within each sample, include region only if a_r > median over all rows
mask_open_regions = a_arr > q_a_region

# combined
combined_mask = mask_open_tss_rows & mask_open_regions

sub_long = long_df[combined_mask].copy()
sub_gene_col = gene_col[combined_mask]
sub_d = sub_long["d_genomic"].to_numpy()
sub_g = sub_long["g_abs"].to_numpy()
sub_focus = sub_long["is_tss"].to_numpy()

C_A_rows = []
for name, fn_key, kwargs in MODELS:
    if fn_key == "tss_only":
        w = MODEL_FNS[fn_key](sub_d, sub_focus)
    else:
        w = MODEL_FNS[fn_key](sub_d, **kwargs)
    med, mean, n_genes = per_gene_spearman(w, sub_g, sub_gene_col)
    pool_rho, _ = spearmanr(w, sub_g)
    C_A_rows.append(
        dict(
            model=name,
            family=fn_key,
            params=json.dumps(kwargs),
            median_rho=med,
            mean_rho=mean,
            pooled_rho=float(pool_rho),
            n_genes_scored=n_genes,
        )
    )

C_A_df = pd.DataFrame(C_A_rows).sort_values("median_rho", ascending=False).reset_index(drop=True)
C_A_df.to_csv(OUT_DIR / "framing_C_A_leaderboard.csv", index=False)
print("wrote framing_C_A_leaderboard.csv  (rows kept:", len(sub_long), ")")

# Framing C for B: gated expression prediction.
# The TSS-only and uniform models don't depend on gating the same way, but for
# consistency we restrict to samples with open TSS and multiply w_r by the
# region-open indicator inside the sum.
gated_a = a_arr * mask_open_regions.astype(np.float32)
restrict_samples = np.isin(sample_col, samples_open_tss)

# keep a restricted long-frame for scoring (only samples with open TSS, keep
# all regions so per-sample sums are well-defined)
restrict_d = d_signed[restrict_samples]
restrict_a = gated_a[restrict_samples]
restrict_samp = sample_col[restrict_samples]
restrict_focus = focus_col[restrict_samples]

C_B_rows = []
meta_restrict = meta_df[meta_df["sample_idx"].isin(samples_open_tss)].reset_index(drop=True)
for name, fn_key, kwargs in MODELS:
    if fn_key == "tss_only":
        w = MODEL_FNS[fn_key](restrict_d, restrict_focus)
    else:
        w = MODEL_FNS[fn_key](restrict_d, **kwargs)
    preds_per_sample_full = np.zeros(n_samples, dtype=np.float64)
    np.add.at(preds_per_sample_full, restrict_samp, w * restrict_a)
    m = per_gene_metrics(preds_per_sample_full, meta_df)
    C_B_rows.append(dict(model=name, family=fn_key, params=json.dumps(kwargs), **m))

C_B_df = pd.DataFrame(C_B_rows).sort_values("pearson", ascending=False).reset_index(drop=True)
C_B_df.to_csv(OUT_DIR / "framing_C_B_leaderboard.csv", index=False)
print("wrote framing_C_B_leaderboard.csv")


# ---------------------------------------------------------------------------
# 7) Figures
# ---------------------------------------------------------------------------

# 7.1 empirical decay curves
fig, ax = plt.subplots(figsize=(7, 4.5))
d_plot = decay_df["bin_center"].to_numpy()
ax.plot(d_plot, decay_df["mean_g"], "o-", label="all regions", color="#1f77b4")
ax.plot(d_plot, decay_df["mean_g_access"], "s-", label="accessible (a_r > median)", color="#2ca02c")
ax.plot(d_plot, decay_df["mean_g_closed"], "^-", label="closed (a_r < median)", color="#d62728")
ax.set_xscale("log")
ax.set_xlabel("|distance TSS -> region|  (bp, log scale)")
ax.set_ylabel("mean |GET motif-only importance|")
ax.set_title("Empirical decay of |g_r| with distance (fine-tuned hepatocytes)")
ax.legend()
fig.tight_layout()
fig.savefig(OUT_DIR / "empirical_decay.png", dpi=150)
plt.close(fig)

# 7.2 framing A leaderboard
fig, ax = plt.subplots(figsize=(9, 10))
top_A = A_df.head(25)
y = np.arange(len(top_A))
ax.barh(y, top_A["median_rho"], color="#4c72b0")
ax.set_yticks(y)
ax.set_yticklabels(top_A["model"])
ax.invert_yaxis()
ax.axvline(0, color="k", lw=0.6)
ax.set_xlabel("per-gene median Spearman(w, |g_r|)")
ax.set_title("Framing A: how well does a simple model predict GET's learned per-region importance?")
fig.tight_layout()
fig.savefig(OUT_DIR / "framing_A_leaderboard.png", dpi=150)
plt.close(fig)

# 7.3 framing B leaderboard
fig, ax = plt.subplots(figsize=(9, 10))
top_B = B_df.head(25)
y = np.arange(len(top_B))
bar_colors = ["#888888" if m == "GET_finetuned" else "#cccccc" if m == "a_TSS_only" else "#4c72b0" for m in top_B["model"]]
ax.barh(y, top_B["pearson"], color=bar_colors)
ax.set_yticks(y)
ax.set_yticklabels(top_B["model"])
ax.invert_yaxis()
ax.axvline(0, color="k", lw=0.6)
ax.set_xlabel("per-gene Pearson(pred, observed log10 TPM+1)")
ax.set_title("Framing B: ABC-style expression prediction (gene-level)")
fig.tight_layout()
fig.savefig(OUT_DIR / "framing_B_leaderboard.png", dpi=150)
plt.close(fig)

# 7.4 parametric sweeps: exp-decay tau
def sweep_family(family_name):
    return A_df[A_df["family"] == family_name].copy()

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
for family_name, marker in [("exp", "o"), ("linear", "s"), ("cutoff", "^"), ("power", "D"), ("loginv", "v")]:
    sub = sweep_family(family_name)
    if len(sub) == 0:
        continue
    axes[0].plot(range(len(sub)), sub["median_rho"], marker + "-", label=family_name)
for family_name, marker in [("exp", "o"), ("linear", "s"), ("cutoff", "^"), ("power", "D"), ("loginv", "v")]:
    sub = B_df[B_df["family"] == family_name]
    if len(sub) == 0:
        continue
    axes[1].plot(range(len(sub)), sub["pearson"], marker + "-", label=family_name)
axes[0].set_title("Framing A: median per-gene Spearman by family")
axes[0].set_xlabel("parameter index (see leaderboard CSV)")
axes[0].set_ylabel("median rho")
axes[0].legend()
axes[1].set_title("Framing B: per-gene Pearson by family")
axes[1].set_xlabel("parameter index (see leaderboard CSV)")
axes[1].set_ylabel("Pearson r")
axes[1].legend()
fig.tight_layout()
fig.savefig(OUT_DIR / "family_sweeps.png", dpi=150)
plt.close(fig)

# 7.5 comparison A vs C_A (with vs without open-chromatin gating) for top families
fig, ax = plt.subplots(figsize=(9, 6))
merged_AC = A_df.merge(C_A_df, on="model", suffixes=("_A", "_CA"))
ax.scatter(merged_AC["median_rho_A"], merged_AC["median_rho_CA"], s=35, alpha=0.75)
lim_lo = min(merged_AC["median_rho_A"].min(), merged_AC["median_rho_CA"].min()) - 0.02
lim_hi = max(merged_AC["median_rho_A"].max(), merged_AC["median_rho_CA"].max()) + 0.02
ax.plot([lim_lo, lim_hi], [lim_lo, lim_hi], "k--", lw=0.6)
for _, row in merged_AC.iterrows():
    ax.annotate(row["model"], (row["median_rho_A"], row["median_rho_CA"]), fontsize=7, alpha=0.8)
ax.set_xlabel("Framing A  median rho  (all regions)")
ax.set_ylabel("Framing C_A  median rho  (open-chromatin gated)")
ax.set_title("Effect of open-chromatin gating on model rankings")
fig.tight_layout()
fig.savefig(OUT_DIR / "framing_A_vs_C.png", dpi=150)
plt.close(fig)


# ---------------------------------------------------------------------------
# 8) Summary JSON
# ---------------------------------------------------------------------------

summary = dict(
    ft_zarr=str(FT_ZARR),
    n_samples=int(n_samples),
    n_genes=int(meta_df["gene"].nunique()),
    n_regions_per_sample=200,
    target="|g_r| = |sum over 282 motif channels of J[r,m] * x[r,m]|",
    jacobian_source="fine-tuned LoRA hepatocytes",
    per_gene_scoring=True,
    median_a_tss_threshold=q_a_tss,
    median_a_region_threshold=q_a_region,
    framing_A_best=A_df.iloc[0].to_dict(),
    framing_B_best=B_df.iloc[0].to_dict(),
    framing_C_A_best=C_A_df.iloc[0].to_dict(),
    framing_C_B_best=C_B_df.iloc[0].to_dict(),
    GET_B_pearson=float(B_df.loc[B_df["model"] == "GET_finetuned", "pearson"].iloc[0]),
    a_TSS_only_B_pearson=float(B_df.loc[B_df["model"] == "a_TSS_only", "pearson"].iloc[0]),
)
(OUT_DIR / "summary_distance.json").write_text(json.dumps(summary, indent=2))
print("wrote summary_distance.json")

print("DONE.")
