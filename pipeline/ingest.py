"""Download Statcast pitch data and save it as monthly Parquet files.

Usage:
    python -m pipeline.ingest --season 2023
    python -m pipeline.ingest --season 2023 --start 2023-04-01 --end 2023-04-07   # quick test
    python -m pipeline.ingest --season 2023 --force                                # re-download

Output: data/raw/statcast_<season>_<MM>.parquet (one file per month, taken pitches only).
"""
from __future__ import annotations

import argparse
import calendar
from datetime import date
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Taken pitches = the batter did not swing, so the umpire made the call.
CALLED_DESCRIPTIONS = {"called_strike", "ball", "blocked_ball"}
STRIKE = "called_strike"

# Columns needed downstream (features, bias metrics, joins). Keeps files small.
KEEP_COLUMNS = [
    "game_pk", "game_date", "game_type", "at_bat_number", "pitch_number",
    "home_team", "away_team", "inning_topbot",
    "batter", "pitcher", "stand", "p_throws", "fielder_2",  # fielder_2 = catcher
    "pitch_type", "release_speed", "pfx_x", "pfx_z",
    "plate_x", "plate_z", "sz_top", "sz_bot",
    "balls", "strikes", "description", "zone",
]


def month_ranges(season: int, start: date | None, end: date | None):
    """Yield (month, first_day, last_day) for each month in the season window."""
    lo = start or date(season, 3, 1)
    hi = end or date(season, 11, 30)
    y, m = lo.year, lo.month
    while (y, m) <= (hi.year, hi.month):
        first = max(lo, date(y, m, 1))
        last = min(hi, date(y, m, calendar.monthrange(y, m)[1]))
        yield m, first, last
        m += 1
        if m > 12:
            y, m = y + 1, 1


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Keep regular-season taken pitches with a location, and add the label."""
    df = df[df["description"].isin(CALLED_DESCRIPTIONS)]
    if "game_type" in df.columns:
        df = df[df["game_type"] == "R"]
    df = df.dropna(subset=["plate_x", "plate_z", "sz_top", "sz_bot"])
    cols = [c for c in KEEP_COLUMNS if c in df.columns]
    df = df[cols].copy()
    df["called_strike"] = (df["description"] == STRIKE).astype("int8")
    return df.drop_duplicates(subset=["game_pk", "at_bat_number", "pitch_number"])


def fetch_with_retry(fetch, first: date, last: date, retries: int = 4):
    """Call pybaseball's statcast, retrying dropped connections with backoff."""
    import time

    import requests

    for attempt in range(retries):
        try:
            return fetch(start_dt=first.isoformat(), end_dt=last.isoformat(), verbose=False)
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:
                raise
            wait = 5 * 2 ** attempt
            print(f"  connection error ({type(e).__name__}); retrying in {wait}s "
                  f"[{attempt + 1}/{retries - 1}]")
            time.sleep(wait)


def ingest(season: int, start: date | None = None, end: date | None = None,
           force: bool = False) -> list[Path]:
    from pybaseball import statcast  # imported here so the module loads without it

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for month, first, last in month_ranges(season, start, end):
        out = RAW_DIR / f"statcast_{season}_{month:02d}.parquet"
        if out.exists() and not force:
            print(f"skip {out.name} (exists; use --force to re-download)")
            continue
        print(f"downloading {first} -> {last} ...")
        raw = fetch_with_retry(statcast, first, last)
        df = clean(raw) if raw is not None and not raw.empty else None
        if df is None or df.empty:
            print(f"  no taken pitches for {first} -> {last}; not writing a file")
            continue
        df.to_parquet(out, index=False)
        written.append(out)
        print(f"  saved {len(df):,} taken pitches -> {out.name}")
    return written


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--start", type=date.fromisoformat, help="YYYY-MM-DD (default Mar 1)")
    p.add_argument("--end", type=date.fromisoformat, help="YYYY-MM-DD (default Nov 30)")
    p.add_argument("--force", action="store_true", help="re-download existing months")
    a = p.parse_args()
    ingest(a.season, a.start, a.end, a.force)


if __name__ == "__main__":
    main()
