import pandas as pd

from pipeline.validate import check_pitches, check_umpires


def _pitches(n=4):
    return pd.DataFrame({
        "game_pk": [1] * n, "game_date": ["2023-04-01"] * n,
        "at_bat_number": [1] * n, "pitch_number": list(range(1, n + 1)),
        "batter": [10] * n, "pitcher": [20] * n,
        "plate_x": [0.0] * n, "plate_z": [2.5] * n, "sz_top": [3.5] * n, "sz_bot": [1.5] * n,
        "balls": [0] * n, "strikes": [0] * n,
        "description": ["called_strike", "ball", "ball", "called_strike"][:n],
        "called_strike": [1, 0, 0, 1][:n],
    })


def _levels(results):
    return {r.name: r.level for r in results}


def test_clean_data_has_no_failures():
    assert not [r for r in check_pitches(_pitches()) if r.level == "FAIL"]


def test_duplicate_null_and_label_problems_fail():
    df = _pitches()
    df.loc[1, "pitch_number"] = 1          # duplicate key
    df.loc[2, "plate_x"] = None            # null location
    df.loc[3, "called_strike"] = 0         # label disagrees with description
    lv = _levels(check_pitches(df))
    assert lv["no duplicate pitches"] == "FAIL"
    assert lv["no nulls in plate_x"] == "FAIL"
    assert lv["label matches description"] == "FAIL"


def test_out_of_range_location_is_warn_when_rare_and_fail_when_common():
    big = pd.concat([_pitches()] * 100, ignore_index=True)
    big["pitch_number"] = range(len(big))
    rare = big.copy()
    rare.loc[0, "plate_z"] = -3.5
    assert _levels(check_pitches(rare))["plausible pitch locations"] == "WARN"
    common = big.copy()
    common.loc[:20, "plate_z"] = -3.5
    assert _levels(check_pitches(common))["plausible pitch locations"] == "FAIL"


def test_unsorted_rows_warn():
    df = _pitches().iloc[::-1]
    assert _levels(check_pitches(df))["rows in game order"] == "WARN"


def test_umpire_coverage():
    pitches = _pitches()
    umps = pd.DataFrame({"game_pk": [2], "umpire_id": [7], "umpire_name": ["X"]})
    lv = _levels(check_umpires(pitches, umps))
    assert lv["every game has a plate umpire"] == "FAIL"
    assert lv["every umpire game has pitches"] == "WARN"
