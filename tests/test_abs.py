"""The feeds here are synthetic, shaped like the real 2026 game feed the probe saw."""
import numpy as np
import pandas as pd
import pytest

from pipeline.abs import (apply_original_calls, challenge_events, expected_challenges,
                          extract_challenges, find_matches)


def _pitch(n, code, review=None):
    event = {"isPitch": True, "pitchNumber": n, "details": {"call": {"code": code}, "code": code}}
    if review:
        event["reviewDetails"] = review
    return event


def _review(overturned, player_id, team=110, in_progress=False):
    return {"isOverturned": overturned, "inProgress": in_progress, "reviewType": "MJ",
            "challengeTeamId": team, "player": {"id": player_id, "fullName": f"P{player_id}"}}


FEED = {
    "gamePk": 7,
    "gameData": {"absChallenges": {"hasChallenges": True,
                                   "away": {"usedSuccessful": 1, "usedFailed": 1},
                                   "home": {"usedSuccessful": 1, "usedFailed": 0}}},
    "liveData": {"plays": {"allPlays": [
        # Batter 10 challenges pitch 2: strike overturned, so the feed shows a ball.
        {"about": {"atBatIndex": 0, "inning": 1},
         "matchup": {"batter": {"id": 10}, "pitcher": {"id": 20}},
         "result": {"description": "A grounds out."},
         "playEvents": [_pitch(1, "B"), _pitch(2, "B", _review(True, 10)),
                        {"isPitch": False, "details": {"description": "Mound visit"}},
                        _pitch(3, "X")]},
        # Catcher 30 challenges the last pitch; stored on the play, overturned to a strike.
        {"about": {"atBatIndex": 1, "inning": 1},
         "matchup": {"batter": {"id": 11}, "pitcher": {"id": 20}},
         "result": {"description": "C challenged (pitch result), call on the field was overturned: "
                                   "B called out on strikes."},
         "reviewDetails": _review(True, 30, team=138),
         "playEvents": [_pitch(1, "C"), _pitch(2, "C")]},
        # Pitcher 20 challenges and loses: the call stands.
        {"about": {"atBatIndex": 2, "inning": 2},
         "matchup": {"batter": {"id": 12}, "pitcher": {"id": 20}},
         "result": {"description": "D walks."},
         "playEvents": [_pitch(1, "B", _review(False, 20, team=138))]},
        # A replay review of a play at first base is not an ABS challenge.
        {"about": {"atBatIndex": 3, "inning": 2},
         "matchup": {"batter": {"id": 13}, "pitcher": {"id": 20}},
         "result": {"description": "Team challenged (play at 1st), call overturned: E singles."},
         "reviewDetails": _review(True, 0),
         "playEvents": [_pitch(1, "X")]},
        # A challenge still in progress is skipped.
        {"about": {"atBatIndex": 4, "inning": 3},
         "matchup": {"batter": {"id": 14}, "pitcher": {"id": 20}},
         "result": {"description": ""},
         "playEvents": [_pitch(1, "C", _review(False, 14, in_progress=True))]},
    ]}},
}


def test_extract_challenges_recovers_original_calls_and_roles():
    rows = {(r["at_bat_number"], r["pitch_number"]): r for r in extract_challenges(7, FEED)}
    assert set(rows) == {(1, 2), (2, 2), (3, 1)}

    batter = rows[(1, 2)]
    assert (batter["final_call"], batter["original_call"]) == ("B", "C")
    assert batter["challenger_role"] == "batter" and batter["source"] == "pitch"

    catcher = rows[(2, 2)]
    assert (catcher["final_call"], catcher["original_call"]) == ("C", "B")
    assert catcher["challenger_role"] == "catcher" and catcher["source"] == "play"

    pitcher = rows[(3, 1)]
    assert pitcher["original_call"] == "B" and not pitcher["is_overturned"]
    assert pitcher["challenger_role"] == "pitcher"


def test_expected_challenges_sums_both_teams():
    assert expected_challenges(FEED) == 3
    assert expected_challenges({"gameData": {}}) is None


def test_apply_original_calls_restores_only_overturned_pitches():
    pitches = pd.DataFrame({"game_pk": 7, "at_bat_number": [1, 1, 2, 3],
                            "pitch_number": [1, 2, 2, 1], "called_strike": [0, 0, 1, 0]})
    challenges = pd.DataFrame(extract_challenges(7, FEED))
    out = apply_original_calls(pitches, challenges).sort_values(["at_bat_number", "pitch_number"])
    assert out["called_strike"].tolist() == [0, 1, 0, 0]
    assert out["challenged"].tolist() == [False, True, True, True]
    assert out["is_overturned"].tolist() == [False, True, True, False]


def test_probe_helpers_still_find_review_fields():
    keys, _ = find_matches(FEED)
    assert "liveData.plays.allPlays[].playEvents[].reviewDetails" in keys
    assert len(challenge_events(FEED)) == 3


def test_2026_leaderboard_requires_challenge_data(tmp_path):
    from analysis.umpire_stats import run
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({"game_pk": [1], "game_date": ["2026-04-01"], "plate_x": [0.0], "plate_z": [2.5],
                  "sz_top": [3.4], "sz_bot": [1.6], "balls": [0], "strikes": [0], "stand": ["R"],
                  "p_throws": ["R"], "called_strike": [1], "description": ["called_strike"]}
                 ).to_parquet(raw / "statcast_2026_04.parquet")
    with pytest.raises(SystemExit, match="pipeline.abs --season 2026"):
        run(2026, raw_dir=raw, reports_dir=tmp_path, processed_dir=tmp_path)
