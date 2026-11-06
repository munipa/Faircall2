"""Fetch the home-plate umpire for each game from the MLB Stats API and join it to pitches.

Usage:
    python -m pipeline.umpires --season 2023
    python -m pipeline.umpires --season 2023 --start 2023-04-01 --end 2023-04-07   # quick test

Output: data/raw/umpires_<season>.parquet with columns
    game_pk, game_date, umpire_id, umpire_name
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
HOME_PLATE = "Home Plate"
CHUNK_DAYS = 30  # schedule handles long ranges; chunking keeps responses small and retries cheap


def parse_schedule(payload: dict) -> list[dict]:
    """Extract one home-plate umpire row per completed regular-season game."""
    rows = []
    for day in payload.get("dates", []):
        for g in day.get("games", []):
            if g.get("gameType") != "R":
                continue
            if g.get("status", {}).get("abstractGameState") != "Final":
                continue
            plate = [o["official"] for o in g.get("officials", [])
                     if o.get("officialType") == HOME_PLATE]
            if not plate:
                continue
            rows.append({
                "game_pk": g["gamePk"],
                "game_date": day["date"],
                "umpire_id": plate[0]["id"],
                "umpire_name": plate[0]["fullName"],
            })
    return rows


def fetch_range(start: date, end: date, retries: int = 3) -> list[dict]:
    params = {"sportId": 1, "startDate": start.isoformat(), "endDate": end.isoformat(),
              "hydrate": "officials"}
    for attempt in range(retries):
        try:
            r = requests.get(SCHEDULE_URL, params=params, timeout=60)
            r.raise_for_status()
            return parse_schedule(r.json())
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def ingest(season: int, start: date | None = None, end: date | None = None) -> Path:
    lo = start or date(season, 3, 1)
    hi = end or date(season, 11, 30)
    rows, cur = [], lo
    while cur <= hi:
        chunk_end = min(cur + timedelta(days=CHUNK_DAYS - 1), hi)
        print(f"fetching umpires {cur} -> {chunk_end} ...")
        rows += fetch_range(cur, chunk_end)
        cur = chunk_end + timedelta(days=1)

    df = pd.DataFrame(rows, columns=["game_pk", "game_date", "umpire_id", "umpire_name"])
    df = df.drop_duplicates("game_pk")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if (start is None and end is None) else f"_{lo}_{hi}"
    out = RAW_DIR / f"umpires_{season}{suffix}.parquet"
    df.to_parquet(out, index=False)
    print(f"saved {len(df):,} games, {df['umpire_id'].nunique()} umpires -> {out.name}")
    return out


def attach_umpires(pitches: pd.DataFrame, umpires: pd.DataFrame) -> pd.DataFrame:
    """Left-join the plate umpire onto pitches by game_pk (unmatched games get NaN)."""
    cols = ["game_pk", "umpire_id", "umpire_name"]
    return pitches.merge(umpires[cols], on="game_pk", how="left", validate="many_to_one")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--start", type=date.fromisoformat)
    p.add_argument("--end", type=date.fromisoformat)
    a = p.parse_args()
    ingest(a.season, a.start, a.end)


if __name__ == "__main__":
    main()
