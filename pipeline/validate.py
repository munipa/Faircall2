"""Data-quality checks for the raw Statcast + umpire files.

Usage:
    python -m pipeline.validate --season 2023

Prints a PASS / WARN / FAIL report and exits with code 1 if any check FAILs.
"""
from __future__ import annotations

import argparse
import glob
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

REQUIRED = ["game_pk", "game_date", "at_bat_number", "pitch_number", "batter", "pitcher",
            "plate_x", "plate_z", "sz_top", "sz_bot", "balls", "strikes",
            "description", "called_strike"]
MUST_BE_COMPLETE = ["game_pk", "plate_x", "plate_z", "sz_top", "sz_bot", "balls", "strikes",
                    "called_strike"]
KEY = ["game_pk", "at_bat_number", "pitch_number"]

# Plausible physical ranges, in feet. Outside these is almost certainly a tracking error.
X_RANGE = (-4.0, 4.0)
Z_RANGE = (-1.0, 6.0)
MAX_OUT_OF_RANGE_FRAC = 0.01   # more than 1% bad locations -> FAIL, any -> WARN
MIN_UMPIRE_PITCHES = 1000      # below this an umpire's metrics are too noisy to rank


@dataclass
class Result:
    level: str   # PASS | WARN | FAIL
    name: str
    detail: str


def _r(ok: bool, name: str, detail: str, fail_level: str = "FAIL") -> Result:
    return Result("PASS" if ok else fail_level, name, detail)


def check_pitches(df: pd.DataFrame) -> list[Result]:
    out = []
    missing = [c for c in REQUIRED if c not in df.columns]
    out.append(_r(not missing, "required columns", f"missing: {missing}" if missing else "all present"))
    if missing:
        return out  # the rest depends on these columns

    dupes = int(df.duplicated(KEY).sum())
    out.append(_r(dupes == 0, "no duplicate pitches", f"{dupes} duplicates"))

    for col in MUST_BE_COMPLETE:
        n = int(df[col].isna().sum())
        out.append(_r(n == 0, f"no nulls in {col}", f"{n} nulls"))
    for col in ("release_speed", "pfx_x", "pfx_z"):
        if col in df.columns:
            n = int(df[col].isna().sum())
            out.append(_r(n == 0, f"nulls in {col}", f"{n} nulls ({n / len(df):.3%})", "WARN"))

    bad = ((df["plate_x"] < X_RANGE[0]) | (df["plate_x"] > X_RANGE[1]) |
           (df["plate_z"] < Z_RANGE[0]) | (df["plate_z"] > Z_RANGE[1]))
    n, frac = int(bad.sum()), float(bad.mean())
    level = "PASS" if n == 0 else ("FAIL" if frac > MAX_OUT_OF_RANGE_FRAC else "WARN")
    out.append(Result(level, "plausible pitch locations",
                      f"{n} pitches outside x{X_RANGE} / z{Z_RANGE} ({frac:.3%}); drop or flag in features"))

    n = int((df["sz_top"] <= df["sz_bot"]).sum())
    out.append(_r(n == 0, "sz_top above sz_bot", f"{n} rows invalid"))

    n = int((df["called_strike"] != (df["description"] == "called_strike").astype(int)).sum())
    out.append(_r(n == 0, "label matches description", f"{n} mismatches"))

    n = int((~df["balls"].between(0, 3) | ~df["strikes"].between(0, 2)).sum())
    out.append(_r(n == 0, "valid counts (0-3 balls, 0-2 strikes)", f"{n} rows invalid"))

    ordered = df.sort_values(KEY).index.equals(df.index)
    out.append(_r(ordered, "rows in game order",
                  "sorted" if ordered else "NOT sorted; features.py must sort by game_pk, at_bat_number, "
                  "pitch_number before computing previous-call features", "WARN"))
    return out


def check_umpires(pitches: pd.DataFrame, umpires: pd.DataFrame) -> list[Result]:
    out = []
    dupes = int(umpires.duplicated("game_pk").sum())
    out.append(_r(dupes == 0, "one umpire row per game", f"{dupes} duplicate games"))

    no_ump = set(pitches["game_pk"]) - set(umpires["game_pk"])
    out.append(_r(not no_ump, "every game has a plate umpire", f"{len(no_ump)} games without one"))
    no_pitch = set(umpires["game_pk"]) - set(pitches["game_pk"])
    out.append(_r(not no_pitch, "every umpire game has pitches", f"{len(no_pitch)} games without pitches",
                  "WARN"))

    per_ump = pitches.merge(umpires[["game_pk", "umpire_id"]], on="game_pk").groupby("umpire_id").size()
    low = int((per_ump < MIN_UMPIRE_PITCHES).sum())
    out.append(_r(low == 0, f"umpires with >= {MIN_UMPIRE_PITCHES} pitches",
                  f"{low} of {len(per_ump)} umpires below threshold; exclude or shrink them in analysis",
                  "WARN"))
    return out


def load(season: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted(glob.glob(str(RAW_DIR / f"statcast_{season}_*.parquet")))
    if not files:
        raise SystemExit(f"no statcast_{season}_*.parquet files in {RAW_DIR}; run pipeline.ingest first")
    ump_file = RAW_DIR / f"umpires_{season}.parquet"
    if not ump_file.exists():
        raise SystemExit(f"{ump_file.name} not found; run pipeline.umpires first")
    pitches = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    return pitches, pd.read_parquet(ump_file)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    season = p.parse_args().season

    pitches, umpires = load(season)
    print(f"Season {season}: {len(pitches):,} pitches, {pitches['game_pk'].nunique():,} games, "
          f"{len(umpires):,} umpire rows\n")
    results = check_pitches(pitches) + check_umpires(pitches, umpires)
    for r in results:
        print(f"[{r.level}] {r.name}: {r.detail}")

    months = pd.to_datetime(pitches["game_date"]).dt.month.value_counts().sort_index()
    print("\npitches per month:", months.to_dict())
    fails = sum(r.level == "FAIL" for r in results)
    warns = sum(r.level == "WARN" for r in results)
    print(f"\n{fails} FAIL, {warns} WARN")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
