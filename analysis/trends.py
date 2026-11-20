"""Umpire accuracy across seasons, and whether the measured zone itself moved.

For each season: accuracy against the measured zone, missed calls per game,
close-pitch accuracy, and Statcast's average zone top and bottom. A change in the
zone measurement can look like a change in umpires, so both are shown together.
From 2026 the umpires' original calls are restored before scoring (pipeline.abs).

It also asks whether umpire accuracy is a stable trait: how well one season's
accuracy predicts the next, using the per-season leaderboards.

Usage:
    python -m analysis.trends                       # every season with data
    python -m analysis.trends --seasons 2021 2022 2023 2024 2025 2026

Writes: reports/trends.md and reports/trends.png
"""
from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path

import numpy as np
import pandas as pd

from models.baseline import BALL_RADIUS_FT, RAW_DIR, REPORTS_DIR, TARGET, add_features, load_seasons

ABS_SEASON = 2026
CLOSE_FT = 2 / 12


def available_seasons(raw_dir: Path = RAW_DIR) -> list[int]:
    found = {int(m.group(1)) for f in glob.glob(str(raw_dir / "statcast_*_*.parquet"))
             if (m := re.search(r"statcast_(\d{4})_", Path(f).name))}
    return sorted(found)


def season_summary(season: int, raw_dir: Path = RAW_DIR) -> dict:
    df = add_features(load_seasons([season], raw_dir))
    restored = None
    if season >= ABS_SEASON:
        path = raw_dir / f"abs_challenges_{season}.parquet"
        if not path.exists():
            raise SystemExit(f"run: python -m pipeline.abs --season {season}")
        from pipeline.abs import apply_original_calls
        df = apply_original_calls(df, pd.read_parquet(path))
        restored = int(df["is_overturned"].sum())
    correct = df[TARGET] == df["in_zone"]
    close = (df["edge_dist"] - BALL_RADIUS_FT).abs() <= CLOSE_FT
    games = df["game_pk"].nunique()
    return {
        "season": season, "pitches": len(df), "games": games,
        "accuracy": correct.mean(), "missed_per_game": (~correct).sum() / games,
        "close_accuracy": correct[close].mean(), "strike_rate": df[TARGET].mean(),
        "in_zone_share": df["in_zone"].mean(),
        "sz_top_in": df["sz_top"].mean() * 12, "sz_bot_in": df["sz_bot"].mean() * 12,
        "restored": restored,
    }


def year_to_year(reports_dir: Path, seasons: list[int]) -> pd.DataFrame:
    """Correlation of umpire accuracy between consecutive seasons' leaderboards."""
    boards = {}
    for s in seasons:
        path = reports_dir / f"umpire_leaderboard_{s}.csv"
        if path.exists():
            boards[s] = pd.read_csv(path)[["umpire_id", "accuracy", "close_accuracy",
                                          "extra_strikes_per_100"]]
    rows = []
    for a, b in zip(seasons, seasons[1:]):
        if a in boards and b in boards:
            both = boards[a].merge(boards[b], on="umpire_id", suffixes=("_a", "_b"))
            if len(both) >= 5:
                rows.append({"season_from": a, "season_to": b, "umpires": len(both),
                             "accuracy_r": both["accuracy_a"].corr(both["accuracy_b"]),
                             "extra_strikes_r": both["extra_strikes_per_100_a"].corr(
                                 both["extra_strikes_per_100_b"])})
    return pd.DataFrame(rows)


def _markdown(summary: pd.DataFrame, persistence: pd.DataFrame) -> str:
    lines = ["# Umpire accuracy across seasons", "",
             "| Season | Calls | Accuracy | Missed per game | Close-pitch accuracy | "
             "Strike rate | Zone top (in) | Zone bottom (in) |", "|---|---|---|---|---|---|---|---|"]
    for r in summary.itertuples():
        mark = " (ABS)" if r.season >= ABS_SEASON else ""
        lines.append(f"| {r.season}{mark} | {r.pitches:,} | {r.accuracy:.1%} | "
                     f"{r.missed_per_game:.1f} | {r.close_accuracy:.1%} | {r.strike_rate:.1%} | "
                     f"{r.sz_top_in:.2f} | {r.sz_bot_in:.2f} |")
    first, last = summary.iloc[0], summary.iloc[-1]
    pre = summary[summary["season"] < ABS_SEASON]
    lines += ["", "## Reading the trend", "",
              f"- Missed calls per game went from {first.missed_per_game:.1f} in "
              f"{int(first.season)} to {last.missed_per_game:.1f} in {int(last.season)}."]
    if len(pre) >= 2:
        drift = pre["sz_top_in"].max() - pre["sz_top_in"].min()
        lines.append(f"- Before ABS, Statcast's average zone top moved by up to {drift:.2f} inches "
                     "between seasons. Part of any year-to-year change can come from the "
                     "measurement, not the umpires, so treat small changes with care.")
    if (summary["season"] >= ABS_SEASON).any():
        abs_row = summary[summary["season"] >= ABS_SEASON].iloc[0]
        lines.append(f"- {int(abs_row.season)} uses a height-based ABS zone and the umpires' "
                     f"original calls ({int(abs_row.restored or 0):,} overturned calls restored), "
                     "so compare it with earlier seasons cautiously.")
    if not persistence.empty:
        lines += ["", "## Is umpire accuracy a stable trait?", "",
                  "Correlation of each umpire's numbers from one season to the next "
                  "(1 = perfectly consistent, 0 = no relationship).", "",
                  "| Seasons | Umpires in both | Accuracy | Extra strikes |", "|---|---|---|---|"]
        for r in persistence.itertuples():
            lines.append(f"| {r.season_from}→{r.season_to} | {r.umpires} | {r.accuracy_r:.2f} | "
                         f"{r.extra_strikes_r:.2f} |")
        lines += ["", f"Average: accuracy {persistence['accuracy_r'].mean():.2f}, "
                  f"extra strikes {persistence['extra_strikes_r'].mean():.2f}. "
                  "Higher means umpires' tendencies carry over, so they reflect the umpire "
                  "rather than luck."]
    return "\n".join(lines) + "\n"


def _plot(summary: pd.DataFrame, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping the chart")
        return
    fig, ax = plt.subplots(figsize=(8, 4.5))
    pre = summary[summary["season"] < ABS_SEASON]
    post = summary[summary["season"] >= ABS_SEASON]
    ax.plot(pre["season"], pre["missed_per_game"], "o-", color="#1f4e79", linewidth=2,
            label="Missed calls per game")
    if not post.empty:
        ax.plot(post["season"], post["missed_per_game"], "o", color="#c8553d", markersize=9,
                label="2026: umpires' original calls (ABS zone)")
    for r in summary.itertuples():
        ax.annotate(f"{r.missed_per_game:.1f}", (r.season, r.missed_per_game),
                    textcoords="offset points", xytext=(0, 9), ha="center", fontsize=10)
    ax.set_xticks(summary["season"])
    ax.set_ylabel("Missed ball-strike calls per game")
    ax.set_title("Umpire misses by season (measured zone)")
    ax.set_ylim(0, max(summary["missed_per_game"]) * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def run(seasons: list[int] | None = None, raw_dir: Path = RAW_DIR,
        reports_dir: Path = REPORTS_DIR) -> pd.DataFrame:
    seasons = seasons or available_seasons(raw_dir)
    if not seasons:
        raise SystemExit(f"no statcast files in {raw_dir}")
    rows = []
    for s in seasons:
        print(f"summarizing {s} ...")
        rows.append(season_summary(s, raw_dir))
    summary = pd.DataFrame(rows)
    persistence = year_to_year(reports_dir, seasons)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = _markdown(summary, persistence)
    (reports_dir / "trends.md").write_text(report)
    summary.to_csv(reports_dir / "trends.csv", index=False)       # read by the app
    _plot(summary, reports_dir / "trends.png")
    print("\n" + report)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--seasons", type=int, nargs="+")
    a = p.parse_args()
    run(a.seasons)


if __name__ == "__main__":
    main()
