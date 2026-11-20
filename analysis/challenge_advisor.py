"""Challenge advisor: how likely an ABS challenge is to be overturned, and how teams use them.

The key input is how far the pitch was on the WRONG side of the zone for the call:
positive inches means the call looks wrong (a strike outside, or a ball inside),
negative means it looks right. A logistic model adds the call, the count and who
challenged, and is validated with cross-validation grouped by game on real 2026
challenges. It's then applied to every 2026 umpire miss to show which misses
were worth challenging and how much each team left on the table.

The location comes from pitch tracking, which players don't see when they decide,
so treat the model as a post-game guide and an upper bound on good decisions.

Usage:
    python -m analysis.challenge_advisor --season 2026

Writes: reports/challenge_advisor_<season>.md and .json (the model, for the app)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from models.baseline import BALL_RADIUS_FT, RAW_DIR, REPORTS_DIR, TARGET

FEATURES = ["wrong_side_in", "strike_call", "two_strikes", "three_balls", "by_catcher",
            "by_pitcher"]
KEYS = ["game_pk", "at_bat_number", "pitch_number"]


def wrong_side_inches(df: pd.DataFrame) -> pd.Series:
    """Inches the pitch sat on the wrong side of the zone for the call (positive = looks wrong)."""
    outside = (df["edge_dist"] - BALL_RADIUS_FT) * 12
    return pd.Series(np.where(df[TARGET] == 1, outside, -outside), index=df.index)


def prepare(season: int, raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    from analysis.bias import load

    pitches = load(season, raw_dir)     # original calls restored
    pitches["wrong_side_in"] = wrong_side_inches(pitches)
    pitches["miss"] = pitches[TARGET] != pitches["in_zone"]
    pitches["batting_team"] = np.where(pitches["inning_topbot"] == "Top",
                                       pitches["away_team"], pitches["home_team"])
    pitches["fielding_team"] = np.where(pitches["inning_topbot"] == "Top",
                                        pitches["home_team"], pitches["away_team"])
    # The team a miss hurt: a wrong strike hurts the batters, a wrong ball the pitchers.
    pitches["hurt_team"] = np.where(pitches[TARGET] == 1, pitches["batting_team"],
                                    pitches["fielding_team"])
    roles = pd.read_parquet(raw_dir / f"abs_challenges_{season}.parquet")[KEYS + ["challenger_role"]]
    ch = pitches[pitches["challenged"]].merge(roles, on=KEYS, how="left")
    ch["team"] = np.where(ch["challenger_role"] == "batter", ch["batting_team"], ch["fielding_team"])
    return pitches, add_model_columns(ch)


def add_model_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["wrong_side_in"] = out["wrong_side_in"].clip(-6, 6)
    out["strike_call"] = (out[TARGET] == 1).astype(int)
    out["two_strikes"] = (out["strikes"] == 2).astype(int)
    out["three_balls"] = (out["balls"] == 3).astype(int)
    role = out.get("challenger_role", pd.Series("batter", index=out.index))
    out["by_catcher"] = (role == "catcher").astype(int)
    out["by_pitcher"] = (role == "pitcher").astype(int)
    return out


def fit(ch: pd.DataFrame, folds: int = 5) -> dict:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
    from sklearn.model_selection import GroupKFold

    y = ch["is_overturned"].astype(int).to_numpy()
    p = np.empty(len(ch))
    folds = min(folds, ch["game_pk"].nunique())
    for train, test in GroupKFold(n_splits=folds).split(ch, groups=ch["game_pk"]):
        m = LogisticRegression(max_iter=1000).fit(ch[FEATURES].iloc[train], y[train])
        p[test] = m.predict_proba(ch[FEATURES].iloc[test])[:, 1]
    base = np.full(len(y), y.mean())
    final = LogisticRegression(max_iter=1000).fit(ch[FEATURES], y)
    return {
        "p": p,
        "metrics": {"challenges": int(len(y)), "overturn_rate": float(y.mean()),
                    "auc": float(roc_auc_score(y, p)),
                    "brier": float(brier_score_loss(y, p)),
                    "brier_baseline": float(brier_score_loss(y, base)),
                    "log_loss": float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6))),
                    "log_loss_baseline": float(log_loss(y, base)),
                    "accuracy": float(((p >= 0.5) == y).mean())},
        "model": {"features": FEATURES, "intercept": float(final.intercept_[0]),
                  "coefficients": dict(zip(FEATURES, map(float, final.coef_[0])))},
    }


def predict(model: dict, wrong_side_in: float, strike_call: bool, balls: int = 0,
            strikes: int = 0, challenger: str = "batter") -> float:
    """P(overturn) for one pitch, from the saved model (used by the app)."""
    x = {"wrong_side_in": max(-6.0, min(6.0, wrong_side_in)), "strike_call": int(strike_call),
         "two_strikes": int(strikes == 2), "three_balls": int(balls == 3),
         "by_catcher": int(challenger == "catcher"), "by_pitcher": int(challenger == "pitcher")}
    z = model["intercept"] + sum(model["coefficients"][f] * x[f] for f in model["features"])
    return float(1 / (1 + np.exp(-z)))


BANDS = [-np.inf, -2, -1, 0, 1, 2, np.inf]
BAND_LABELS = ["Call looks right by 2+ in", "Looks right by 1–2 in", "Looks right by 0–1 in",
               "Looks wrong by 0–1 in", "Looks wrong by 1–2 in", "Looks wrong by 2+ in"]


def _rate(s):
    return f"{s.mean():.1%} ({int(s.sum()):,} of {len(s):,})" if len(s) else "n/a"


def build_report(pitches: pd.DataFrame, ch: pd.DataFrame, result: dict, season: int) -> str:
    m = result["metrics"]
    ch = ch.assign(p=result["p"])
    games = pitches["game_pk"].nunique()
    lines = [f"# Challenge advisor, {season}", "",
             f"Trained and validated on {m['challenges']:,} real ABS challenges "
             "(5-fold cross-validation grouped by game).", "",
             "| Model | AUC | Brier | Log loss | Accuracy |", "|---|---|---|---|---|",
             f"| Always guess the average ({m['overturn_rate']:.1%}) | 0.500 | "
             f"{m['brier_baseline']:.3f} | {m['log_loss_baseline']:.3f} | "
             f"{max(m['overturn_rate'], 1 - m['overturn_rate']):.1%} |",
             f"| Challenge advisor | {m['auc']:.3f} | {m['brier']:.3f} | {m['log_loss']:.3f} | "
             f"{m['accuracy']:.1%} |", "",
             "## Overturn rate by where the pitch was", "",
             "| Pitch vs the call | Challenges | Actually overturned | Advisor predicted |",
             "|---|---|---|---|"]
    bands = pd.cut(ch["wrong_side_in"], BANDS, labels=BAND_LABELS)
    for band, g in ch.groupby(bands, observed=False):
        if len(g):
            lines.append(f"| {band} | {len(g):,} | {_rate(g['is_overturned'])} | {g['p'].mean():.1%} |")
    coef = result["model"]["coefficients"]
    per_inch = np.exp(coef["wrong_side_in"])
    lines += ["", "## What matters", "",
              ("- Location almost completely decides the outcome: a pitch on the wrong side "
               "of the zone for the call is overturned nearly every time, and one on the right "
               "side almost never is." if per_inch > 100 else
               f"- Each inch the pitch is on the wrong side multiplies the odds of an overturn "
               f"by {per_inch:.1f}."),
              f"- Catchers' challenges succeed more than batters' at the same location "
              f"(odds × {np.exp(coef['by_catcher']):.2f}); pitchers' "
              f"(odds × {np.exp(coef['by_pitcher']):.2f}).", ""]

    miss = pitches[pitches["miss"]]
    worth = miss[miss["wrong_side_in"] >= 1]
    lines += ["## Missed opportunities", "",
              f"- Umpire misses: {len(miss):,} ({len(miss) / games:.1f} per game); "
              f"teams challenged {_rate(miss['challenged'])}.",
              f"- Misses by 1+ inch, which the advisor rates as likely overturns: {len(worth):,}; "
              f"challenged {_rate(worth['challenged'])}.",
              f"- Challenges on calls that were right (wasted): "
              f"{_rate(~pitches.loc[pitches['challenged'], 'miss'])}."]
    k = miss[(miss[TARGET] == 1) & (miss["strikes"] == 2)]
    bb = miss[(miss[TARGET] == 0) & (miss["balls"] == 3)]
    lines += [f"- Wrong strike threes (a batter rung up on a ball): {len(k):,}; "
              f"fixed by ABS {_rate(k['is_overturned'])}.",
              f"- Wrong ball fours (a walk on a strike): {len(bb):,}; "
              f"fixed by ABS {_rate(bb['is_overturned'])}.", ""]

    teams = ch.groupby("team").agg(challenges=("is_overturned", "size"),
                                   overturned=("is_overturned", "mean"))
    left = miss[~miss["challenged"] & (miss["wrong_side_in"] >= 1)].groupby("hurt_team").size()
    teams["clear_misses_left"] = left.reindex(teams.index).fillna(0).astype(int)
    teams = teams.sort_values("overturned", ascending=False)
    lines += ["## Teams", "",
              "Clear misses left = misses of 1+ inch that hurt the team and were not challenged.", "",
              "| Team | Challenges | Overturned | Clear misses left |", "|---|---|---|---|"]
    for team, r in teams.iterrows():
        lines.append(f"| {team} | {int(r.challenges):,} | {r.overturned:.1%} | "
                     f"{int(r.clear_misses_left):,} |")
    lines += ["", "## How to read this", "",
              "- Location comes from pitch tracking, which players can't see in the moment, "
              "so the advisor is an upper bound on good decisions and a post-game guide.",
              "- FairCall's zone agrees with ABS rulings on 99.9% of challenged pitches, so "
              "location almost decides the outcome; the useful part is spotting which "
              "misses deserved a challenge."]
    return "\n".join(lines) + "\n"


def run(season: int = 2026, raw_dir: Path = RAW_DIR, reports_dir: Path = REPORTS_DIR) -> dict:
    pitches, ch = prepare(season, raw_dir)
    result = fit(ch)
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(pitches, ch, result, season)
    (reports_dir / f"challenge_advisor_{season}.md").write_text(report)
    (reports_dir / f"challenge_advisor_{season}.json").write_text(json.dumps(
        {"season": season, **result["metrics"], **result["model"]}, indent=1))
    print(report)
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, default=2026)
    run(p.parse_args().season)


if __name__ == "__main__":
    main()
