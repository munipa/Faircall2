"""Where umpires lean: extra strikes by count, situation, zone region and catcher.

The leaderboard's model knows the count and handedness, so it can't show bias
by count. Here the expectation comes from LOCATION ONLY (where the pitch crossed
and the batter's zone), cross-fitted within the season by game. Anything left
over (more strikes than location alone explains) is a lean:

    extra strikes per 100 = 100 x (called strikes - expected from location) / pitches

with a 95% interval from the model's own variance. From 2026 the umpires'
original calls are restored first (pipeline.abs).

Usage:
    python -m analysis.bias --season 2025
    python -m analysis.bias --season 2025 --catcher-names    # look up catcher names online

Writes: reports/bias_<season>.md, reports/bias_counts_<season>.png,
        reports/catcher_framing_<season>.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from models.baseline import (BALL_RADIUS_FT, RAW_DIR, REPORTS_DIR, TARGET, add_features,
                             load_seasons)

ABS_SEASON = 2026
CLOSE_FT = 2 / 12
Z = 1.96
LOCATION_FEATURES = ["plate_x", "plate_z", "sz_top", "sz_bot", "z_norm", "abs_x", "edge_dist"]
PITCH_GROUPS = {
    "Fastball": {"FF", "SI", "FC", "FT", "FA"},
    "Breaking ball": {"SL", "CU", "KC", "SV", "ST", "CS", "SC"},
    "Offspeed": {"CH", "FS", "FO", "EP", "KN"},
}


# ---------------------------------------------------------------- data

def load(season: int, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    df = add_features(load_seasons([season], raw_dir))
    if season >= ABS_SEASON:
        path = raw_dir / f"abs_challenges_{season}.parquet"
        if not path.exists():
            raise SystemExit(f"run: python -m pipeline.abs --season {season}")
        from pipeline.abs import apply_original_calls
        df = apply_original_calls(df, pd.read_parquet(path))
    return add_situation(df)


def add_situation(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["count"] = out["balls"].astype(int).astype(str) + "-" + out["strikes"].astype(int).astype(str)
    if "inning_topbot" in out:
        out["batting_side"] = np.where(out["inning_topbot"] == "Top", "Away team batting",
                                       "Home team batting")
    # Previous pitch in the same plate appearance. Only taken pitches are stored,
    # so a missing previous pitch means it was swung at (or this is the first pitch).
    keys = ["game_pk", "at_bat_number"]
    prev = out[keys + ["pitch_number", TARGET]].copy()
    prev["pitch_number"] = prev["pitch_number"] + 1
    prev = prev.rename(columns={TARGET: "_prev_call"})
    out = out.merge(prev, on=keys + ["pitch_number"], how="left")
    out["previous_pitch"] = np.select(
        [out["pitch_number"] == 1, out["_prev_call"] == 1, out["_prev_call"] == 0],
        ["First pitch", "After a called strike", "After a called ball"],
        "After a swing or other")
    out = out.drop(columns="_prev_call")
    out["matchup"] = ("Batter " + out["stand"].astype(str) + " vs pitcher "
                      + out.get("p_throws", pd.Series("?", index=out.index)).astype(str))
    if "pitch_type" in out:
        group = pd.Series("Other", index=out.index)
        for name, codes in PITCH_GROUPS.items():
            group[out["pitch_type"].isin(codes)] = name
        out["pitch_group"] = group
    out["close"] = (out["edge_dist"] - BALL_RADIUS_FT).abs() <= CLOSE_FT
    vertical = np.maximum(out["sz_bot"] - out["plate_z"], out["plate_z"] - out["sz_top"])
    horizontal = out["plate_x"].abs() - 17 / 24
    out["region"] = np.where(
        horizontal >= vertical,
        np.where(out["x_batter"] > 0, "Inside edge", "Outside edge"),
        np.where(out["plate_z"] > (out["sz_top"] + out["sz_bot"]) / 2, "Top edge", "Bottom edge"))
    return out


# ---------------------------------------------------------------- expectation

def location_expectation(df: pd.DataFrame, folds: int = 5, seed: int = 595,
                         model: str = "xgboost") -> np.ndarray:
    """Cross-fitted strike probability from location alone, folds grouped by game."""
    from sklearn.model_selection import GroupKFold

    def make():
        if model == "logistic":
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import make_pipeline
            from sklearn.preprocessing import SplineTransformer
            return make_pipeline(SplineTransformer(n_knots=8), LogisticRegression(max_iter=2000))
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                             min_child_weight=20, reg_lambda=5.0, subsample=0.8,
                             colsample_bytree=0.8, eval_metric="logloss", n_jobs=-1,
                             random_state=seed)

    p = np.empty(len(df))
    X = df[LOCATION_FEATURES]
    for i, (train, test) in enumerate(GroupKFold(n_splits=folds).split(df, groups=df["game_pk"])):
        print(f"  fold {i + 1}/{folds}: location-only model on {len(train):,} pitches ...")
        est = make().fit(X.iloc[train], df[TARGET].iloc[train])
        p[test] = est.predict_proba(X.iloc[test])[:, 1]
    return p


# ---------------------------------------------------------------- breakdowns

def lean(df: pd.DataFrame, by: str | list[str], min_pitches: int = 200) -> pd.DataFrame:
    """Extra strikes per 100 pitches (95% CI) for each group."""
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({
        "pitches": g.size(),
        "called": g[TARGET].sum(),
        "expected": g["p_loc"].sum(),
        "var": g["p_loc"].apply(lambda p: (p * (1 - p)).sum()),
    }).reset_index()
    out = out[out["pitches"] >= min_pitches].copy()
    out["extra_per_100"] = (out["called"] - out["expected"]) / out["pitches"] * 100
    half = Z * np.sqrt(out["var"]) / out["pitches"] * 100
    out["low"], out["high"] = out["extra_per_100"] - half, out["extra_per_100"] + half
    out["clear"] = np.where(out["low"] > 0, "more strikes",
                            np.where(out["high"] < 0, "fewer strikes", "no clear lean"))
    return out.drop(columns="var")


def catcher_names(ids: list[int]) -> dict[int, str]:
    """Best effort: catcher names from the MLB Stats API (needs internet)."""
    try:
        import requests
        names = {}
        for i in range(0, len(ids), 100):
            chunk = ",".join(str(int(x)) for x in ids[i:i + 100])
            r = requests.get("https://statsapi.mlb.com/api/v1/people",
                             params={"personIds": chunk}, timeout=30)
            r.raise_for_status()
            names.update({p["id"]: p["fullName"] for p in r.json().get("people", [])})
        return names
    except Exception as error:
        print(f"catcher names not available ({error}); showing IDs")
        return {}


# ---------------------------------------------------------------- outputs

def _s(x):
    return f"{x:+.2f}"


def _table(df: pd.DataFrame, label: str, column: str) -> list[str]:
    rows = [f"| {label} | Pitches | Extra strikes per 100 (95% CI) | Lean |", "|---|---|---|---|"]
    for r in df.itertuples():
        rows.append(f"| {getattr(r, column)} | {r.pitches:,} | {_s(r.extra_per_100)} "
                    f"({_s(r.low)} to {_s(r.high)}) | {r.clear} |")
    return rows


COUNT_ORDER = [f"{b}-{s}" for b in range(4) for s in range(3)]


def build_report(df: pd.DataFrame, season: int, framing: pd.DataFrame) -> str:
    total = lean(df.assign(all="All pitches"), "all")
    counts = lean(df, "count").set_index("count").reindex(COUNT_ORDER).dropna().reset_index()
    close = df[df["close"]]
    lines = [f"# Where umpires lean, {season}", "",
             f"{len(df):,} taken pitches. Expected strikes come from location alone "
             "(cross-fitted by game), so these show what besides location changes the call.",
             f"League check: {_s(total['extra_per_100'].iloc[0])} extra strikes per 100 "
             "(should be about zero).", "",
             "## By count", "", *_table(counts, "Count", "count"), "",
             "A positive number means umpires call more strikes in that count than location "
             "alone explains.", ""]
    hitter = counts[counts["count"].isin(["3-0", "3-1", "2-0"])]["extra_per_100"].mean()
    pitcher = counts[counts["count"].isin(["0-2", "1-2"])]["extra_per_100"].mean()
    if np.isfinite(hitter) and np.isfinite(pitcher):
        lines += [f"In hitter's counts (2-0, 3-0, 3-1) umpires average {_s(hitter)} extra strikes "
                  f"per 100; in pitcher's counts (0-2, 1-2) {_s(pitcher)}. The zone grows when "
                  "the batter is ahead and shrinks when the pitcher is ahead." if hitter > pitcher
                  else f"Hitter's counts {_s(hitter)}, pitcher's counts {_s(pitcher)}.", ""]
    sections = [("Previous pitch", "previous_pitch"), ("Home or away", "batting_side"),
                ("Handedness", "matchup"), ("Pitch type", "pitch_group")]
    for title, col in sections:
        if col in df:
            lines += [f"## By {title.lower()}", "", *_table(lean(df, col), title, col), ""]
    lines += ["## Close pitches by zone region", "",
              "Only pitches within 2 inches of the zone edge.", "",
              *_table(lean(close, "region"), "Region", "region"), ""]
    if not framing.empty:
        lines += ["## Catcher framing", "",
                  "Extra strikes per 100 taken pitches a catcher receives, beyond location. "
                  f"{len(framing)} catchers with at least 1,500 taken pitches.", "",
                  "Best framers:", "", *_table(framing.head(5), "Catcher", "catcher"), "",
                  "Weakest framers:", "", *_table(framing.tail(5).iloc[::-1], "Catcher", "catcher"), ""]
    lines += ["## How to read this", "",
              "- \"No clear lean\" means the 95% interval includes zero.",
              "- These are league-wide patterns; the leaderboard shows individual umpires.",
              "- Leans can come from umpires, catchers or the measured zone; the breakdowns "
              "help separate them but don't prove cause."]
    return "\n".join(lines) + "\n"


def plot_counts(counts: pd.DataFrame, season: int, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    grid = np.full((4, 3), np.nan)
    for r in counts.itertuples():
        b, s = map(int, r.count.split("-"))
        grid[b, s] = r.extra_per_100
    lim = np.nanmax(np.abs(grid)) or 1
    fig, ax = plt.subplots(figsize=(5.5, 6))
    im = ax.imshow(grid, cmap="RdBu_r", vmin=-lim, vmax=lim)
    for b in range(4):
        for s in range(3):
            if np.isfinite(grid[b, s]):
                ax.text(s, b, f"{grid[b, s]:+.1f}", ha="center", va="center", fontsize=13,
                        color="black")
    ax.set_xticks(range(3), [f"{s} strikes" for s in range(3)])
    ax.set_yticks(range(4), [f"{b} balls" for b in range(4)])
    ax.set_title(f"Extra strikes per 100 by count, {season}\n(beyond location; red = more strikes)")
    fig.colorbar(im, ax=ax, shrink=0.7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run(season: int, *, folds: int = 5, model: str = "xgboost", names: bool = False,
        raw_dir: Path = RAW_DIR, reports_dir: Path = REPORTS_DIR,
        min_catcher: int = 1500) -> dict:
    df = load(season, raw_dir)
    print(f"{season}: {len(df):,} taken pitches")
    df["p_loc"] = location_expectation(df, folds=folds, model=model)
    framing = lean(df, "fielder_2", min_pitches=min_catcher).sort_values(
        "extra_per_100", ascending=False).reset_index(drop=True)
    lookup = catcher_names(framing["fielder_2"].tolist()) if names and len(framing) else {}
    framing["catcher"] = [lookup.get(int(i), f"Catcher {int(i)}") for i in framing["fielder_2"]]
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(df, season, framing)
    (reports_dir / f"bias_{season}.md").write_text(report)
    framing.to_csv(reports_dir / f"catcher_framing_{season}.csv", index=False)
    counts = lean(df, "count")
    plot_counts(counts, season, reports_dir / f"bias_counts_{season}.png")
    print("\n" + report)
    return {"counts": counts, "framing": framing, "pitches": len(df)}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--catcher-names", action="store_true", help="look up names online")
    a = p.parse_args()
    run(a.season, folds=a.folds, names=a.catcher_names)


if __name__ == "__main__":
    main()
