"""2026 ABS challenges: recover the umpire's original call on every challenged pitch.

Statcast and the MLB Stats API both record the call AFTER a challenge. The game
feed marks each challenged pitch with `reviewDetails` (who challenged, whether it
was overturned), so the original call is the recorded call, flipped when the
challenge succeeded. A challenge on the last pitch of a plate appearance is
stored on the play instead of the pitch; those are matched to the last pitch.

Usage:
    python -m pipeline.abs --season 2026          # all games, resumable
    python -m pipeline.abs --probe                 # inspect the feed (3 games)

Reads:  data/raw/umpires_<season>.parquet (the season's games),
        data/raw/statcast_<season>_*.parquet (for the report)
Writes: data/raw/abs_challenges_<season>.parquet   one row per challenged pitch
        data/raw/abs_games/<season>/<gamePk>.json  per-game cache
        reports/abs_challenges_<season>.md          what happened in challenges

Keys match Statcast: at_bat_number = feed atBatIndex + 1, pitch_number = pitchNumber.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REPORTS_DIR = ROOT / "reports"
PROBE_DIR = RAW_DIR / "abs_probe"
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
FEED_URL = "https://statsapi.mlb.com/api/v1.1/game/{pk}/feed/live"
PATTERN = re.compile(r"review|challeng|\babs\b|overturn", re.IGNORECASE)
KEYS = ["game_pk", "at_bat_number", "pitch_number"]
FLIP = {"B": "C", "C": "B"}
COLUMNS = KEYS + ["final_call", "original_call", "is_overturned", "challenge_team_id",
                  "challenger_id", "challenger", "challenger_role", "batter_id", "pitcher_id",
                  "inning", "source"]


def _get(url: str, **params) -> dict:
    import requests

    response = requests.get(url, params=params or None, timeout=60)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------- parsing

def _call_code(event: dict) -> str | None:
    details = event.get("details", {})
    return (details.get("call") or {}).get("code") or details.get("code")


def extract_challenges(game_pk: int, pbp: dict) -> list[dict]:
    """One row per ABS-challenged pitch in a playByPlay (or live feed) response."""
    plays = pbp.get("allPlays") or pbp.get("liveData", {}).get("plays", {}).get("allPlays", [])
    rows = {}
    for play in plays:
        about, matchup = play.get("about", {}), play.get("matchup", {})
        batter = (matchup.get("batter") or {}).get("id")
        pitcher = (matchup.get("pitcher") or {}).get("id")
        pitches = [e for e in play.get("playEvents", []) if e.get("isPitch")]

        def add(event: dict, review: dict, source: str):
            final = _call_code(event)
            if final not in FLIP or review.get("inProgress"):
                return
            overturned = bool(review.get("isOverturned"))
            who = review.get("player") or {}
            role = ("batter" if who.get("id") == batter else
                    "pitcher" if who.get("id") == pitcher else "catcher")
            key = (game_pk, about.get("atBatIndex", -1) + 1, event.get("pitchNumber"))
            rows[key] = {
                "game_pk": game_pk, "at_bat_number": key[1], "pitch_number": key[2],
                "final_call": final, "original_call": FLIP[final] if overturned else final,
                "is_overturned": overturned, "challenge_team_id": review.get("challengeTeamId"),
                "challenger_id": who.get("id"), "challenger": who.get("fullName"),
                "challenger_role": role, "batter_id": batter, "pitcher_id": pitcher,
                "inning": about.get("inning"), "source": source,
            }

        for event in pitches:
            if event.get("reviewDetails"):
                add(event, event["reviewDetails"], "pitch")
        # A challenge on the plate appearance's last pitch is stored on the play.
        description = (play.get("result") or {}).get("description") or ""
        if play.get("reviewDetails") and "(pitch result)" in description and pitches:
            last = pitches[-1]
            if not last.get("reviewDetails"):
                add(last, play["reviewDetails"], "play")
    return list(rows.values())


def apply_original_calls(pitches: pd.DataFrame, challenges: pd.DataFrame) -> pd.DataFrame:
    """Replace called_strike with the umpire's original call on overturned pitches."""
    cols = KEYS + ["original_call", "is_overturned", "final_call"]
    out = pitches.drop(columns=[c for c in cols[3:] + ["challenged"] if c in pitches])
    out = out.merge(challenges[cols], on=KEYS, how="left", validate="one_to_one")
    out["challenged"] = out["original_call"].notna()
    out["is_overturned"] = out["is_overturned"].astype("boolean").fillna(False).astype(bool)
    original = out["original_call"].map({"C": 1, "B": 0})
    out["called_strike"] = np.where(out["challenged"], original, out["called_strike"]).astype("int8")
    return out


# ---------------------------------------------------------------- download

def season_games(season: int, raw_dir: Path = RAW_DIR) -> list[int]:
    path = raw_dir / f"umpires_{season}.parquet"
    if path.exists():
        return sorted(pd.read_parquet(path)["game_pk"].astype(int).unique().tolist())
    payload = _get(SCHEDULE_URL, sportId=1, season=season, gameType="R")
    return sorted({g["gamePk"] for d in payload.get("dates", []) for g in d.get("games", [])
                   if g.get("status", {}).get("abstractGameState") == "Final"})


FEED_FIELDS = ("gameData,absChallenges,hasChallenges,away,home,usedSuccessful,usedFailed,"
               "liveData,plays,allPlays,about,atBatIndex,inning,matchup,batter,pitcher,id,fullName,"
               "result,description,reviewDetails,isOverturned,inProgress,reviewType,challengeTeamId,"
               "player,playEvents,isPitch,pitchNumber,details,call,code")


def expected_challenges(feed: dict) -> int | None:
    """Challenges MLB's own totals say were used in the game (successful + failed)."""
    totals = feed.get("gameData", {}).get("absChallenges")
    if not totals:
        return None
    return sum(int((totals.get(side) or {}).get(k) or 0)
               for side in ("away", "home") for k in ("usedSuccessful", "usedFailed"))


def _fetch_game(pk: int, cache: Path) -> dict:
    path = cache / f"{pk}.json"
    if path.exists():
        return json.loads(path.read_text())
    feed = _get(FEED_URL.format(pk=pk), fields=FEED_FIELDS)
    if not feed.get("liveData", {}).get("plays", {}).get("allPlays"):
        feed = _get(FEED_URL.format(pk=pk))     # the trimmed request failed; take it all
    record = {"rows": extract_challenges(pk, feed), "expected": expected_challenges(feed)}
    path.write_text(json.dumps(record))
    return record


def collect(season: int, workers: int = 8, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    games = season_games(season, raw_dir)
    cache = raw_dir / "abs_games" / str(season)
    cache.mkdir(parents=True, exist_ok=True)
    todo = [pk for pk in games if not (cache / f"{pk}.json").exists()]
    print(f"{season}: {len(games):,} games, {len(games) - len(todo):,} already cached")
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_game, pk, cache): pk for pk in todo}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
            except Exception as error:   # keep going; rerun to retry
                failed.append(futures[future])
                print(f"  game {futures[future]} failed: {error}")
            if i % 200 == 0 or i == len(todo):
                print(f"  {i:,}/{len(todo):,} games downloaded")
    if failed:
        print(f"{len(failed)} games failed; rerun the same command to retry them")
    records = {pk: json.loads((cache / f"{pk}.json").read_text())
               for pk in games if (cache / f"{pk}.json").exists()}
    df = pd.DataFrame([r for rec in records.values() for r in rec["rows"]], columns=COLUMNS)
    df.to_parquet(raw_dir / f"abs_challenges_{season}.parquet", index=False)
    expected = [rec["expected"] for rec in records.values() if rec["expected"] is not None]
    mismatched = sum(1 for rec in records.values()
                     if rec["expected"] is not None and rec["expected"] != len(rec["rows"]))
    df.attrs.update(games=len(games), downloaded=len(records), failed=len(failed),
                    expected=sum(expected) if expected else None, mismatched=mismatched)
    return df


# ---------------------------------------------------------------- report

def _rate(s: pd.Series) -> str:
    return f"{s.mean():.1%} ({int(s.sum()):,} of {len(s):,})" if len(s) else "n/a"


def challenge_report(challenges: pd.DataFrame, season: int, raw_dir: Path = RAW_DIR,
                     games: int | None = None) -> str:
    lines = [f"# ABS challenges, {season}", ""]
    info = challenges.attrs
    if info.get("downloaded") is not None:
        lines += [f"Games downloaded: {info['downloaded']:,} of {info['games']:,}"
                  + (f" ({info['failed']} failed; rerun to retry)" if info.get("failed") else ""), ""]
    if challenges.empty:
        return "\n".join(lines + ["No challenges found."]) + "\n"
    games = games or challenges["game_pk"].nunique()
    lines += [
        f"- Challenges: {len(challenges):,} in {games:,} games "
        f"({len(challenges) / games:.2f} per game)",
        f"- Overturned: {_rate(challenges['is_overturned'])}",
        f"- Original strikes overturned to balls: "
        f"{int((challenges.is_overturned & (challenges.original_call == 'C')).sum()):,}; "
        f"balls overturned to strikes: "
        f"{int((challenges.is_overturned & (challenges.original_call == 'B')).sum()):,}",
        f"- Found on the pitch: {int((challenges.source == 'pitch').sum()):,}; "
        f"on the last pitch of a plate appearance: {int((challenges.source == 'play').sum()):,}",
        "", "## By who challenged", "", "| Challenger | Challenges | Overturned |", "|---|---|---|",
    ]
    for role, g in challenges.groupby("challenger_role"):
        lines.append(f"| {role} | {len(g):,} | {_rate(g['is_overturned'])} |")

    try:
        from models.baseline import BALL_RADIUS_FT, add_features, load_seasons
        pitches = add_features(load_seasons([season], raw_dir))
        joined = challenges.merge(pitches[KEYS + ["edge_dist", "called_strike"]], on=KEYS, how="left")
        matched = joined["edge_dist"].notna()
        agree = (joined.loc[matched, "called_strike"] == (joined.loc[matched, "final_call"] == "C")).mean()
        lines += ["", "## Data checks", ""]
        if info.get("expected") is not None:
            lines.append(f"- Challenges found vs MLB's game totals: {len(challenges):,} vs "
                         f"{info['expected']:,}; games that differ: {info['mismatched']:,}")
        lines += [f"- Challenges matched to a Statcast pitch: {_rate(matched)}",
                  f"- Statcast call agrees with the feed's final call: {agree:.1%}"]

        # ABS's ruling is the official zone: does our measured-zone definition match it?
        ruled = joined.loc[matched]
        zone_ok = (ruled["edge_dist"] <= BALL_RADIUS_FT).astype(int) == (ruled["final_call"] == "C")
        lines += ["", "## Our zone vs ABS's official rulings", "",
                  f"On challenged pitches, ABS's ruling is the official answer. FairCall's "
                  f"measured zone (ball touching the zone) agrees with it on "
                  f"**{zone_ok.mean():.1%}** of {len(ruled):,} pitches."]

        # Every umpire miss in the season, and how many ABS fixed.
        full = apply_original_calls(pitches, challenges)
        miss = full["called_strike"] != full["in_zone"]
        fixed = miss & full["is_overturned"]
        games_played = full["game_pk"].nunique()
        lines += ["", "## How many umpire misses ABS fixed", "",
                  f"- Umpire misses (original call vs measured zone): {int(miss.sum()):,} "
                  f"({miss.sum() / games_played:.1f} per game)",
                  f"- Challenged: {_rate(full.loc[miss, 'challenged'])}",
                  f"- Fixed by ABS: {_rate(fixed[miss])}, so "
                  f"{(miss.sum() - fixed.sum()) / games_played:.1f} misses per game still stand",
                  f"- Challenges that were not on a miss (wasted): "
                  f"{_rate(~miss[full['challenged']])}"]
        inches = (full.loc[miss, "edge_dist"] - BALL_RADIUS_FT).abs() * 12
        bands = pd.cut(inches, [0, 0.5, 1, 2, 3, np.inf],
                       labels=["under 0.5 in", "0.5–1 in", "1–2 in", "2–3 in", "3 in or more"],
                       include_lowest=True)
        lines += ["", "Misses by how far the pitch was from the zone edge:", "",
                  "| Distance | Misses | Challenged | Fixed by ABS |", "|---|---|---|---|"]
        for band, g in full.loc[miss].groupby(bands, observed=False):
            lines.append(f"| {band} | {len(g):,} | {_rate(g['challenged'])} | "
                         f"{_rate(g['is_overturned'])} |")
    except SystemExit as error:
        lines += ["", f"Statcast checks skipped: {error}"]

    lines += ["", "## How to read this", "",
              "- The original call is the recorded call, flipped when the challenge was overturned.",
              "- Challenges are chosen by players, so these pitches are not a random sample "
              "of close calls."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- probe

def find_matches(obj, path: str = "", keys=None, values=None):
    """Every key path whose name, or string value, mentions a review or challenge."""
    keys = keys if keys is not None else defaultdict(list)
    values = values if values is not None else defaultdict(list)
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else k
            if PATTERN.search(k) and len(keys[child]) < 3:
                text = json.dumps(v, default=str)
                keys[child].append(v if len(text) <= 300 else text[:300] + " ...")
            find_matches(v, child, keys, values)
    elif isinstance(obj, list):
        for item in obj:
            find_matches(item, f"{path}[]", keys, values)
    elif isinstance(obj, str) and PATTERN.search(obj) and len(values[path]) < 3:
        values[path].append(obj[:200])
    return keys, values


def challenge_events(feed: dict, limit: int = 25) -> list[dict]:
    found = []
    for play in feed.get("liveData", {}).get("plays", {}).get("allPlays", []):
        for event in play.get("playEvents", []):
            if event.get("reviewDetails") or PATTERN.search(
                    json.dumps(event.get("details", {}).get("description", ""))):
                found.append({"gamePk": feed.get("gamePk"),
                              "atBatIndex": play.get("about", {}).get("atBatIndex"),
                              "playResult": play.get("result", {}).get("description"),
                              "event": event})
                if len(found) >= limit:
                    return found
    return found


def probe(date: str, games: int, out_dir: Path = PROBE_DIR) -> None:
    payload = _get(SCHEDULE_URL, sportId=1, date=date, gameType="R")
    pks = [g["gamePk"] for d in payload.get("dates", []) for g in d.get("games", [])
           if g.get("status", {}).get("abstractGameState") == "Final"][:games]
    if not pks:
        raise SystemExit(f"no final regular-season games on {date}")
    out_dir.mkdir(parents=True, exist_ok=True)
    counts, key_hits, value_hits, examples = Counter(), defaultdict(list), defaultdict(list), []
    for i, pk in enumerate(pks):
        print(f"fetching game {pk} ({i + 1}/{len(pks)}) ...")
        feed = _get(FEED_URL.format(pk=pk))
        if i == 0:
            (out_dir / f"{pk}.json").write_text(json.dumps(feed))
        k, v = find_matches(feed)
        for path, samples in k.items():
            counts[path] += 1
            key_hits[path] = (key_hits[path] + samples)[:3]
        for path, samples in v.items():
            value_hits[path] = (value_hits[path] + samples)[:3]
        examples += challenge_events(feed)
    lines = [f"ABS probe: {len(pks)} games on {date}: {pks}", "", "Fields named for reviews:"]
    for path, n in counts.most_common():
        lines += [f"  {path}  [{n} games]"] + [f"      e.g. {s}" for s in key_hits[path]]
    lines += ["", "Text mentioning reviews:"]
    for path, samples in value_hits.items():
        lines += [f"  {path}"] + [f"      e.g. {s}" for s in samples]
    summary = "\n".join(lines) + "\n"
    (out_dir / "summary.txt").write_text(summary)
    (out_dir / "examples.json").write_text(json.dumps(examples, indent=1, default=str))
    print(summary)


# ---------------------------------------------------------------- main

def run(season: int, workers: int = 8, raw_dir: Path = RAW_DIR,
        reports_dir: Path = REPORTS_DIR) -> pd.DataFrame:
    challenges = collect(season, workers, raw_dir)
    report = challenge_report(challenges, season, raw_dir, games=len(season_games(season, raw_dir)))
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"abs_challenges_{season}.md").write_text(report)
    print("\n" + report)
    return challenges


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--season", type=int, help="collect every challenge in this season")
    p.add_argument("--workers", type=int, default=8, help="parallel downloads (default 8)")
    p.add_argument("--probe", action="store_true", help="inspect how the feed records challenges")
    p.add_argument("--date", default="2026-04-15", help="day to probe")
    p.add_argument("--games", type=int, default=3, help="games to probe")
    a = p.parse_args()
    if a.probe:
        probe(a.date, a.games)
    elif a.season:
        run(a.season, a.workers)
    else:
        p.error("give --season 2026 or --probe")


if __name__ == "__main__":
    main()
