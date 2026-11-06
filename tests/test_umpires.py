import pandas as pd

from pipeline.umpires import attach_umpires, parse_schedule


def _game(pk, game_type="R", state="Final", officials=None):
    return {"gamePk": pk, "gameType": game_type,
            "status": {"abstractGameState": state}, "officials": officials or []}


def _plate(i, name):
    return {"official": {"id": i, "fullName": name}, "officialType": "Home Plate"}


def _base(i, name):
    return {"official": {"id": i, "fullName": name}, "officialType": "First Base"}


def test_parse_schedule_picks_home_plate_only():
    payload = {"dates": [{"date": "2023-04-01", "games": [
        _game(1, officials=[_base(9, "B"), _plate(7, "Plate Ump")]),
        _game(2, game_type="S", officials=[_plate(8, "Spring")]),      # not regular season
        _game(3, state="Preview", officials=[_plate(8, "Future")]),    # not final
        _game(4, officials=[_base(9, "B")]),                           # no plate umpire listed
    ]}]}
    rows = parse_schedule(payload)
    assert rows == [{"game_pk": 1, "game_date": "2023-04-01", "umpire_id": 7,
                     "umpire_name": "Plate Ump"}]


def test_attach_umpires_keeps_all_pitches():
    pitches = pd.DataFrame({"game_pk": [1, 1, 2], "called_strike": [1, 0, 1]})
    umps = pd.DataFrame({"game_pk": [1], "umpire_id": [7], "umpire_name": ["Plate Ump"]})
    out = attach_umpires(pitches, umps)
    assert len(out) == 3
    assert out["umpire_id"].tolist()[:2] == [7, 7] and pd.isna(out["umpire_id"].iloc[2])
