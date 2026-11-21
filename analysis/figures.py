"""Presentation figures, in FairCall's colors.

  strike_zone_<season>.png  The real strike zone vs the rulebook, and how it changes with the count.
  abs_fixes_<season>.png    Which umpire misses ABS challenges fixed (2026 on).

Usage:
    python -m analysis.figures                      # both, for 2025 and 2026
    python -m analysis.figures --zone-season 2024 --abs-season 2026
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from models.baseline import BALL_RADIUS_FT, RAW_DIR, REPORTS_DIR, add_features, load_seasons

CREAM, PAPER, INK, MUTED = "#F2EDE6", "#FBF8F2", "#16212F", "#4A5260"
ORANGE, BLUE, GRAY = "#E07B39", "#2F6DB5", "#7D8794"
DASH = (0, (5, 4))
PLATE_HALF_IN = 8.5


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12})
    return plt


def _zone_axes(ax, title: str) -> None:
    from matplotlib.patches import Rectangle
    ax.set_facecolor(PAPER)
    ax.set_xlim(-18, 18)
    ax.set_ylim(-0.5, 1.5)
    ax.add_patch(Rectangle((-PLATE_HALF_IN, 0), 2 * PLATE_HALF_IN, 1, fill=False, ec=GRAY,
                           lw=2, ls=DASH))
    ax.set_title(title, fontsize=15, fontweight="bold", color=INK, loc="left")
    ax.set_xlabel("Inches from the middle of the plate (catcher's view)", color=MUTED)
    ax.set_yticks([0, 0.5, 1], ["Bottom\nof zone", "Middle", "Top\nof zone"])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _header(fig, title: str, subtitle: str) -> None:
    fig.suptitle(title, fontsize=24, fontweight="bold", color=INK, x=0.06, ha="left", y=0.985)
    fig.text(0.06, 0.915, subtitle, fontsize=12.5, color=MUTED)


def strike_probability_surface(df: pd.DataFrame, xs: np.ndarray, zs: np.ndarray,
                               smooth: float = 2.0, seed: int = 1) -> np.ndarray:
    """Called-strike probability on a grid of (inches across, height within the zone)."""
    from scipy.ndimage import gaussian_filter
    from xgboost import XGBClassifier

    model = XGBClassifier(n_estimators=250, max_depth=6, learning_rate=0.08, min_child_weight=30,
                          subsample=0.8, n_jobs=-1, random_state=seed)
    model.fit(np.column_stack([df["plate_x"] * 12, df["z_norm"]]), df["called_strike"])
    X, Z = np.meshgrid(xs, zs)
    p = model.predict_proba(np.column_stack([X.ravel(), Z.ravel()]))[:, 1].reshape(Z.shape)
    return gaussian_filter(p, smooth)


def strike_zone(season: int, raw_dir: Path = RAW_DIR, reports_dir: Path = REPORTS_DIR,
                df: pd.DataFrame | None = None) -> dict:
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.lines import Line2D

    plt = _plt()
    df = df if df is not None else add_features(load_seasons([season], raw_dir))
    xs, zs = np.linspace(-18, 18, 145), np.linspace(-0.5, 1.5, 161)
    groups = {"all": df, "0-2": df[(df["balls"] == 0) & (df["strikes"] == 2)],
              "3-0": df[(df["balls"] == 3) & (df["strikes"] == 0)]}
    surfaces = {k: strike_probability_surface(v, xs, zs) for k, v in groups.items()}
    cell = (xs[1] - xs[0]) * (zs[1] - zs[0])
    area = {k: float((s >= 0.5).sum() * cell / (2 * PLATE_HALF_IN)) for k, s in surfaces.items()}

    cmap = LinearSegmentedColormap.from_list("faircall", [PAPER, "#C9D6E6", "#5B7FA8", INK])
    fig, (left, right) = plt.subplots(1, 2, figsize=(14, 7.6), facecolor=CREAM)
    image = left.imshow(surfaces["all"], origin="lower", extent=[-18, 18, -0.5, 1.5],
                        aspect="auto", cmap=cmap, vmin=0, vmax=1, interpolation="bilinear")
    left.contour(xs, zs, surfaces["all"], levels=[0.5], colors=INK, linewidths=2.4)
    _zone_axes(left, "Where umpires call strikes")
    bar = fig.colorbar(image, ax=left, fraction=0.046, pad=0.03)
    bar.set_ticks([0, 0.5, 1], labels=["0%", "50%", "100%"])
    bar.set_label("Chance of a called strike", color=MUTED)
    bar.outline.set_visible(False)
    left.legend(handles=[Line2D([], [], color=INK, lw=2.4, label="Real zone (50% strikes)"),
                         Line2D([], [], color=GRAY, lw=2, ls=DASH, label="Rulebook zone")],
                loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False)

    _zone_axes(right, "The zone changes with the count")
    for key, color, width in (("3-0", ORANGE, 2.8), ("all", INK, 2.2), ("0-2", BLUE, 2.8)):
        right.contour(xs, zs, surfaces[key], levels=[0.5], colors=color, linewidths=width)
    right.legend(handles=[
        Line2D([], [], color=ORANGE, lw=2.8, label=f"3-0, batter ahead ({area['3-0']:.0%} of box)"),
        Line2D([], [], color=INK, lw=2.2, label=f"All counts ({area['all']:.0%})"),
        Line2D([], [], color=BLUE, lw=2.8, label=f"0-2, pitcher ahead ({area['0-2']:.0%})"),
        Line2D([], [], color=GRAY, lw=2, ls=DASH, label="Rulebook zone (100%)")],
        loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False, fontsize=11.5)
    _header(fig, "The real strike zone vs the rulebook",
            f"{season} season, {len(df):,} taken pitches. Lines mark where umpires call strikes half "
            "the time; zone heights are scaled to each batter.")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.83, bottom=0.22, wspace=0.28)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"strike_zone_{season}.png"
    fig.savefig(path, dpi=150, facecolor=CREAM)
    plt.close(fig)
    return {"path": path, "area": area}


def abs_fixes(season: int = 2026, raw_dir: Path = RAW_DIR, reports_dir: Path = REPORTS_DIR) -> dict:
    """Every umpire miss on the zone, fixed by a challenge or left standing, plus fix rate by size."""
    from matplotlib.lines import Line2D
    from pipeline.abs import apply_original_calls

    plt = _plt()
    path = raw_dir / f"abs_challenges_{season}.parquet"
    if not path.exists():
        raise SystemExit(f"run: python -m pipeline.abs --season {season}")
    df = apply_original_calls(add_features(load_seasons([season], raw_dir)), pd.read_parquet(path))
    miss = df[df["called_strike"] != df["in_zone"]].copy()
    miss["inches"] = (miss["edge_dist"] - BALL_RADIUS_FT).abs() * 12
    fixed = miss["is_overturned"].to_numpy()
    games = df["game_pk"].nunique()

    fig, (left, right) = plt.subplots(1, 2, figsize=(14, 7.6), facecolor=CREAM,
                                      gridspec_kw={"width_ratios": [1.05, 1]})
    _zone_axes(left, "Every umpire miss")
    # Same size and opacity for both groups, drawn in random order, so the share of
    # orange on screen matches the share of misses that were fixed.
    order = np.random.default_rng(0).permutation(len(miss))
    pts = miss.iloc[order]
    colors = np.where(pts["is_overturned"].to_numpy(), ORANGE, GRAY)
    left.scatter(pts["plate_x"] * 12, pts["z_norm"], s=4, c=colors, alpha=0.45, linewidths=0,
                 rasterized=True)
    left.legend(handles=[
        Line2D([], [], marker="o", ls="", color=ORANGE, ms=8, label=f"Fixed by a challenge ({fixed.sum():,})"),
        Line2D([], [], marker="o", ls="", color=GRAY, ms=8, label=f"Left standing ({(~fixed).sum():,})")],
        loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False)

    bins = [0, 0.5, 1, 2, 3, np.inf]
    labels = ["Under ½ in", "½–1 in", "1–2 in", "2–3 in", "3+ in"]
    miss["band"] = pd.cut(miss["inches"], bins, labels=labels, include_lowest=True)
    rate = miss.groupby("band", observed=False)["is_overturned"].agg(["mean", "size"])
    y = np.arange(len(labels))[::-1]
    right.barh(y, rate["mean"] * 100, color=ORANGE, height=0.62)
    right.barh(y, 100 - rate["mean"] * 100, left=rate["mean"] * 100, color="#E4DDD2", height=0.62)
    for yi, (share, n) in zip(y, rate.itertuples(index=False)):
        right.text(share * 100 + 1.5, yi, f"{share:.0%}", va="center", fontsize=13,
                   fontweight="bold", color=INK)
        right.text(99, yi, f"{n:,} misses", va="center", ha="right", fontsize=11, color=MUTED)
    right.set_yticks(y, labels)
    right.set_xlim(0, 100)
    right.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    right.set_xlabel("Share of misses fixed by a challenge", color=MUTED)
    right.set_ylabel("How far the pitch was from the zone edge", color=MUTED)
    right.set_title("Bigger misses get fixed more often", fontsize=15,
                    fontweight="bold", color=INK, loc="left")
    right.set_facecolor(PAPER)
    for spine in right.spines.values():
        spine.set_visible(False)

    share = fixed.mean()
    _header(fig, f"ABS fixed about 1 in {round(1 / share)} umpire misses" if share else "What ABS fixed",
            f"{season} season: {len(miss):,} missed calls ({len(miss) / games:.1f} per game); "
            f"challenges fixed {share:.0%}, so {(~fixed).sum() / games:.1f} per game still stood.")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.83, bottom=0.22, wspace=0.32)
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / f"abs_fixes_{season}.png"
    fig.savefig(out, dpi=150, facecolor=CREAM)
    plt.close(fig)
    return {"path": out, "misses": int(len(miss)), "fixed": int(fixed.sum())}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--zone-season", type=int, default=2025)
    p.add_argument("--abs-season", type=int, default=2026)
    a = p.parse_args()
    print(strike_zone(a.zone_season))
    print(abs_fixes(a.abs_season))


if __name__ == "__main__":
    main()
