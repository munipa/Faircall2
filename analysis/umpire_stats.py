"""Umpire accuracy and strike-calling tendencies for one season, with uncertainty.

For each home-plate umpire:
  accuracy           share of calls that match the measured zone (Wilson 95% CI)
  missed per game    wrong calls per game
  close accuracy     accuracy on pitches within 2 inches of the zone edge
  extra strikes      strikes called minus strikes the model expected, per 100 pitches
                     (95% CI), overall, with two strikes and with three balls

Expected strikes come from the XGBoost baseline, cross-fitted within the season:
games are split into folds, and each fold is predicted by a model trained on the
others, so every pitch gets a prediction from a model that never saw its game.
Training and predicting in the same season avoids the zone-measurement change
between seasons.

These are consistency audits, not verdicts on individual umpires. Umpires below
the minimum pitch count are left out, and every number carries an interval.

Usage:
    python -m pipeline.umpires --season 2025        # once, to get the umpires
    python -m analysis.umpire_stats --season 2025
    python -m analysis.umpire_stats --season 2025 --min-pitches 2000 --drop-blocked

Reads:  data/raw/statcast_<season>_*.parquet and data/raw/umpires_<season>.parquet
Writes: reports/umpire_leaderboard_<season>.md, .csv and .png,
        data/processed/expected_strikes_<season>.parquet
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from models.baseline import (BALL_RADIUS_FT, PROCESSED_DIR, RAW_DIR, REPORTS_DIR, TARGET,
                             add_features, load_seasons, make_models)

CLOSE_FT = 2 / 12          # "close" = within 2 inches of where the ball would touch the zone
Z = 1.96


# ---------------------------------------------------------------- data

def load_umpires(season: int, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    path = raw_dir / f"umpires_{season}.parquet"
    if not path.exists():
        raise SystemExit(f"{path.name} not found in {raw_dir}; "
                         f"run: python -m pipeline.umpires --season {season}")
    umpires = pd.read_parquet(path)
    if umpires["game_pk"].duplicated().any():
        raise SystemExit(f"{path.name} has more than one umpire for some games")
    return umpires[["game_pk", "umpire_id", "umpire_name"]]


def attach_umpires(pitches: pd.DataFrame, umpires: pd.DataFrame) -> pd.DataFrame:
    base = pitches.drop(columns=["umpire_id", "umpire_name", "umpire"], errors="ignore")
    return base.merge(umpires, on="game_pk", how="left", validate="many_to_one")


# ---------------------------------------------------------------- expected strikes

def expected_strikes(df: pd.DataFrame, folds: int = 5, model: str = "XGBoost",
                     seed: int = 595) -> np.ndarray:
    """Cross-fitted strike probability for every pitch, grouping folds by game."""
    from sklearn.model_selection import GroupKFold

    games = df["game_pk"].nunique()
    if games < folds:
        raise SystemExit(f"need at least {folds} games for {folds} folds, found {games}")
    p = np.empty(len(df))
    for i, (train, test) in enumerate(GroupKFold(n_splits=folds).split(df, groups=df["game_pk"])):
        estimator, columns = make_models(seed)[model]
        print(f"  fold {i + 1}/{folds}: training {model} on {len(train):,} pitches ...")
        estimator.fit(df.iloc[train][columns], df.iloc[train][TARGET])
        p[test] = estimator.predict_proba(df.iloc[test][columns])[:, 1]
    return p


# ---------------------------------------------------------------- uncertainty

def wilson(successes, n, z: float = Z):
    successes, n = np.asarray(successes, float), np.asarray(n, float)
    p = successes / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return center - half, center + half


def _extra(y: pd.Series, p: pd.Series) -> tuple[float, float, float, int]:
    """Extra strikes per 100 pitches with a 95% interval from the model's own variance."""
    n = len(y)
    if n == 0:
        return np.nan, np.nan, np.nan, 0
    diff = (y.sum() - p.sum()) / n * 100
    se = np.sqrt((p * (1 - p)).sum()) / n * 100
    return diff, diff - Z * se, diff + Z * se, n


# ---------------------------------------------------------------- leaderboard

def _summarize(g: pd.DataFrame) -> dict:
    n = len(g)
    correct = int(g["correct_call"].sum())
    close = g[g["close"]]
    extra, extra_lo, extra_hi, _ = _extra(g[TARGET], g["p_strike"])
    two, two_lo, two_hi, n_two = _extra(g.loc[g["strikes"] == 2, TARGET],
                                        g.loc[g["strikes"] == 2, "p_strike"])
    three, three_lo, three_hi, n_three = _extra(g.loc[g["balls"] == 3, TARGET],
                                                g.loc[g["balls"] == 3, "p_strike"])
    return {
        "games": g["game_pk"].nunique(), "pitches": n, "correct": correct,
        "missed_per_game": (n - correct) / g["game_pk"].nunique(),
        "close_pitches": len(close),
        "close_correct": int(close["correct_call"].sum()),
        "extra_strikes_per_100": extra, "extra_low": extra_lo, "extra_high": extra_hi,
        "two_strike_pitches": n_two, "two_strike_extra_per_100": two,
        "two_strike_low": two_lo, "two_strike_high": two_hi,
        "three_ball_pitches": n_three, "three_ball_extra_per_100": three,
        "three_ball_low": three_lo, "three_ball_high": three_hi,
    }


def leaderboard(df: pd.DataFrame, min_pitches: int = 1000) -> tuple[pd.DataFrame, dict]:
    """One row per umpire with at least min_pitches calls, plus a league summary."""
    df = df.copy()
    df["correct_call"] = (df[TARGET] == df["in_zone"]).astype(int)
    df["close"] = (df["edge_dist"] - BALL_RADIUS_FT).abs() <= CLOSE_FT

    league = _summarize(df)
    rated = df.dropna(subset=["umpire_id"])
    rows = [{"umpire_id": int(uid), "umpire": name, **_summarize(g)}
            for (uid, name), g in rated.groupby(["umpire_id", "umpire_name"])]
    board = pd.DataFrame(rows)
    league.update({"umpires_total": len(board),
                   "pitches_without_umpire": int(df["umpire_id"].isna().sum())})
    board = board[board["pitches"] >= min_pitches].copy() if len(board) else board
    league["umpires_rated"] = len(board)
    if board.empty:
        return board, league

    board["accuracy"] = board["correct"] / board["pitches"]
    board["accuracy_low"], board["accuracy_high"] = wilson(board["correct"], board["pitches"])
    board["close_accuracy"] = board["close_correct"] / board["close_pitches"].replace(0, np.nan)
    board["close_low"], board["close_high"] = wilson(board["close_correct"],
                                                     board["close_pitches"].replace(0, np.nan))
    board = board.sort_values("accuracy", ascending=False).reset_index(drop=True)
    board.insert(0, "rank", np.arange(1, len(board) + 1))
    return board, league


# ---------------------------------------------------------------- outputs

def _pct(x):
    return f"{x:.1%}"


def _signed(x):
    return f"{x:+.2f}"


def _table(rows: pd.DataFrame, columns: list[tuple[str, callable]]) -> list[str]:
    head = "| " + " | ".join(name for name, _ in columns) + " |"
    rule = "|" + "---|" * len(columns)
    body = ["| " + " | ".join(fmt(r) for _, fmt in columns) + " |" for r in rows.itertuples()]
    return [head, rule, *body]


ACCURACY_COLUMNS = [
    ("Rank", lambda r: str(r.rank)),
    ("Umpire", lambda r: r.umpire),
    ("Games", lambda r: str(r.games)),
    ("Accuracy (95% CI)", lambda r: f"{_pct(r.accuracy)} ({_pct(r.accuracy_low)}–{_pct(r.accuracy_high)})"),
    ("Missed per game", lambda r: f"{r.missed_per_game:.1f}"),
    ("Close-pitch accuracy", lambda r: _pct(r.close_accuracy)),
]
EXTRA_COLUMNS = [
    ("Umpire", lambda r: r.umpire),
    ("Extra strikes per 100 (95% CI)",
     lambda r: f"{_signed(r.extra_strikes_per_100)} ({_signed(r.extra_low)} to {_signed(r.extra_high)})"),
    ("With two strikes", lambda r: _signed(r.two_strike_extra_per_100)),
    ("With three balls", lambda r: _signed(r.three_ball_extra_per_100)),
]


def _markdown(board: pd.DataFrame, league: dict, season: int, min_pitches: int,
              drop_blocked: bool) -> str:
    acc = league["correct"] / league["pitches"]
    close_acc = league["close_correct"] / max(league["close_pitches"], 1)
    lines = [
        f"# Umpire consistency audit, {season}", "",
        f"{league['pitches']:,} taken pitches in {league['games']:,} games. "
        f"Blocked balls {'excluded' if drop_blocked else 'included'}.",
        f"{league['umpires_rated']} of {league['umpires_total']} umpires have at least "
        f"{min_pitches:,} calls and are rated. {league['pitches_without_umpire']:,} pitches "
        "had no umpire listed.", "",
        "## League", "",
        f"- Accuracy against the measured zone: {_pct(acc)} "
        f"({(league['pitches'] - league['correct']) / league['games']:.1f} missed calls per game)",
        f"- Accuracy on close pitches (within 2 inches of the edge): {_pct(close_acc)}",
        f"- Extra strikes per 100 pitches: {_signed(league['extra_strikes_per_100'])}. "
        "This should be close to zero; it checks that the model's expectations are unbiased.",
        f"- With two strikes: {_signed(league['two_strike_extra_per_100'])}; "
        f"with three balls: {_signed(league['three_ball_extra_per_100'])}",
    ]
    if board.empty:
        return "\n".join(lines + ["", "No umpire reached the minimum pitch count."]) + "\n"
    clear_more = int((board["extra_low"] > 0).sum())
    clear_fewer = int((board["extra_high"] < 0).sum())
    lines += [
        "", "## Most accurate", "", *_table(board.head(10), ACCURACY_COLUMNS),
        "", "## Least accurate", "", *_table(board.tail(10).iloc[::-1], ACCURACY_COLUMNS),
        "", "## Strike-calling tendencies", "",
        f"{clear_more} {'umpire calls' if clear_more == 1 else 'umpires call'} clearly more "
        f"strikes than expected and {clear_fewer} {'calls' if clear_fewer == 1 else 'call'} "
        "clearly fewer (95% interval excludes zero).", "",
        "Most extra strikes:", "",
        *_table(board.nlargest(5, "extra_strikes_per_100"), EXTRA_COLUMNS),
        "", "Fewest extra strikes:", "",
        *_table(board.nsmallest(5, "extra_strikes_per_100"), EXTRA_COLUMNS),
        "", "## How to read this", "",
        "- Accuracy compares each call with the measured zone; a pitch is in if any part "
        "of the ball touches it.",
        "- Extra strikes compare each call with what the model expects umpires in general "
        "to call for the same pitch, count and batter. Positive means more strikes than "
        "the league.",
        "- Ranks near each other are usually not meaningfully different; check whether "
        "the intervals overlap.",
        "- This is a consistency audit, not a verdict on any umpire.",
    ]
    return "\n".join(lines) + "\n"


def _plot(board: pd.DataFrame, league_accuracy: float, season: int, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping the chart")
        return False
    ordered = board.sort_values("accuracy")
    y = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(7, max(3, 0.17 * len(ordered) + 1)))
    ax.hlines(y, ordered["accuracy_low"] * 100, ordered["accuracy_high"] * 100,
              color="#9aa5b1", linewidth=1.2)
    ax.plot(ordered["accuracy"] * 100, y, "o", color="#1f4e79", markersize=3.5)
    ax.axvline(league_accuracy * 100, color="#c8553d", linestyle="--", linewidth=1,
               label=f"League {league_accuracy:.1%}")
    ax.set_yticks(y)
    ax.set_yticklabels(ordered["umpire"], fontsize=6)
    ax.set_xlabel("Calls matching the measured zone (%), with 95% interval")
    ax.set_title(f"Umpire accuracy, {season}")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    ax.margins(y=0.01)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


# ---------------------------------------------------------------- main

def run(season: int, *, min_pitches: int = 1000, folds: int = 5, model: str = "XGBoost",
        drop_blocked: bool = False, raw_dir: Path = RAW_DIR, reports_dir: Path = REPORTS_DIR,
        processed_dir: Path = PROCESSED_DIR, seed: int = 595) -> tuple[pd.DataFrame, dict]:
    pitches = add_features(load_seasons([season], raw_dir))
    if drop_blocked:
        pitches = pitches[pitches["description"] != "blocked_ball"]
    df = attach_umpires(pitches.reset_index(drop=True), load_umpires(season, raw_dir))
    print(f"{season}: {len(df):,} pitches in {df['game_pk'].nunique():,} games")
    df["p_strike"] = expected_strikes(df, folds=folds, model=model, seed=seed)

    board, league = leaderboard(df, min_pitches=min_pitches)
    reports_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    board.to_csv(reports_dir / f"umpire_leaderboard_{season}.csv", index=False)
    report = _markdown(board, league, season, min_pitches, drop_blocked)
    (reports_dir / f"umpire_leaderboard_{season}.md").write_text(report)
    if not board.empty:
        _plot(board, league["correct"] / league["pitches"], season,
              reports_dir / f"umpire_leaderboard_{season}.png")
    keep = [c for c in ["game_pk", "game_date", "at_bat_number", "pitch_number", "umpire_id",
                        "umpire_name", "batter", "pitcher", "fielder_2", "balls", "strikes",
                        TARGET, "in_zone", "edge_dist", "p_strike"] if c in df]
    df[keep].to_parquet(processed_dir / f"expected_strikes_{season}.parquet", index=False)
    print("\n" + report)
    return board, league


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--min-pitches", type=int, default=1000)
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--model", choices=["XGBoost", "Logistic regression"], default="XGBoost")
    p.add_argument("--drop-blocked", action="store_true", help="leave out blocked balls")
    a = p.parse_args()
    run(a.season, min_pitches=a.min_pitches, folds=a.folds, model=a.model,
        drop_blocked=a.drop_blocked)


if __name__ == "__main__":
    main()
