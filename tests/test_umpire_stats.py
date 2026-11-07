"""All pitches here are synthetic and test the logic only."""
import numpy as np
import pandas as pd
import pytest

from analysis.umpire_stats import attach_umpires, leaderboard, load_umpires, run, wilson
from models.baseline import BALL_RADIUS_FT, edge_distance_ft


def test_wilson_interval_contains_rate_and_stays_in_range():
    low, high = wilson(np.array([90, 100]), np.array([100, 100]))
    assert low[0] < 0.9 < high[0]
    assert 0 < low[1] < 1 and high[1] == pytest.approx(1)


def test_attach_umpires_rejects_two_umpires_for_one_game():
    umps = pd.DataFrame({"game_pk": [1, 1], "umpire_id": [7, 8], "umpire_name": ["A", "B"]})
    with pytest.raises(Exception):
        attach_umpires(pd.DataFrame({"game_pk": [1]}), umps)


def test_missing_umpire_file_explains_how_to_fix(tmp_path):
    with pytest.raises(SystemExit, match="pipeline.umpires --season 2025"):
        load_umpires(2025, tmp_path)


def _rows(umpire, n, called, in_zone, p, strikes=0, balls=0):
    return pd.DataFrame({
        "game_pk": np.arange(n) % 10 + 100 * umpire, "umpire_id": umpire,
        "umpire_name": f"Ump {umpire}", "called_strike": called, "in_zone": in_zone,
        "edge_dist": 1.0, "p_strike": p, "strikes": strikes, "balls": balls,
    })


def test_leaderboard_accuracy_extra_strikes_and_minimum():
    df = pd.concat([
        _rows(1, 100, [1] * 90 + [0] * 10, 1, 0.8),     # 90% accurate, 10 extra per 100
        _rows(2, 100, [1] * 70 + [0] * 30, 1, 0.8),     # 70% accurate, 10 fewer per 100
        _rows(3, 20, 1, 1, 0.5),                        # below the minimum
    ], ignore_index=True)
    df.loc[0, "umpire_id"] = np.nan                     # one pitch without an umpire
    board, league = leaderboard(df, min_pitches=50)

    assert board["umpire"].tolist() == ["Ump 1", "Ump 2"]
    assert board["accuracy"].tolist() == pytest.approx([89 / 99, 0.70])
    assert board.loc[1, "extra_strikes_per_100"] == pytest.approx(-10)
    assert board.loc[1, "extra_high"] < 0
    assert league["pitches_without_umpire"] == 1
    assert league["umpires_total"] == 3 and league["umpires_rated"] == 2


def test_close_pitches_are_within_two_inches_of_the_edge():
    df = _rows(1, 4, 1, 1, 0.5)
    # On the edge, 2.4 inches outside, 1.2 inches inside, a foot inside.
    df["edge_dist"] = [BALL_RADIUS_FT, BALL_RADIUS_FT + 0.2, BALL_RADIUS_FT - 0.1, -1.0]
    board, _ = leaderboard(df, min_pitches=1)
    assert board.loc[0, "close_pitches"] == 2


def _season(rng, n=12000):
    df = pd.DataFrame({
        "game_pk": rng.integers(0, 240, n), "game_type": "R",
        "at_bat_number": rng.integers(1, 80, n), "pitch_number": rng.integers(1, 8, n),
        "batter": rng.integers(1, 300, n), "pitcher": rng.integers(1, 300, n),
        "fielder_2": rng.integers(1, 40, n),
        "plate_x": rng.uniform(-1.6, 1.6, n), "plate_z": rng.uniform(0.8, 4.3, n),
        "sz_bot": 1.6, "sz_top": 3.4, "balls": rng.integers(0, 4, n),
        "strikes": rng.integers(0, 3, n), "stand": rng.choice(["L", "R"], n),
        "p_throws": rng.choice(["L", "R"], n), "release_speed": rng.normal(92, 4, n),
        "pfx_x": rng.normal(0, 0.8, n), "pfx_z": rng.normal(1, 0.6, n),
    })
    df["game_date"] = pd.Timestamp("2025-04-01") + pd.to_timedelta(df["game_pk"] % 150, "D")
    umpire = df["game_pk"] % 6                     # 6 umpires, 40 games each
    logit = -14 * (edge_distance_ft(df) - BALL_RADIUS_FT) + 1.2 * (umpire == 0)
    df["called_strike"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype("int8")
    df["description"] = np.where(df["called_strike"] == 1, "called_strike", "ball")
    umps = pd.DataFrame({"game_pk": range(240), "umpire_id": [g % 6 for g in range(240)],
                         "umpire_name": [f"Ump {g % 6}" for g in range(240)]})
    return df, umps


@pytest.mark.parametrize("model", ["Logistic regression", "XGBoost"])
def test_end_to_end_finds_the_umpire_who_calls_extra_strikes(tmp_path, model):
    if model == "XGBoost":
        pytest.importorskip("xgboost")
    rng = np.random.default_rng(595)
    raw = tmp_path / "raw"
    raw.mkdir()
    pitches, umps = _season(rng)
    pitches.to_parquet(raw / "statcast_2025_04.parquet")
    umps.to_parquet(raw / "umpires_2025.parquet")

    board, league = run(2025, min_pitches=500, model=model, raw_dir=raw,
                        reports_dir=tmp_path / "reports", processed_dir=tmp_path / "processed")

    assert len(board) == 6
    top = board.nlargest(1, "extra_strikes_per_100").iloc[0]
    assert top["umpire"] == "Ump 0" and top["extra_low"] > 0
    assert abs(league["extra_strikes_per_100"]) < 1.5   # cross-fitting keeps the league near zero
    for suffix in ("md", "csv"):
        assert (tmp_path / "reports" / f"umpire_leaderboard_2025.{suffix}").exists()
    expected = pd.read_parquet(tmp_path / "processed" / "expected_strikes_2025.parquet")
    assert len(expected) == len(pitches) and expected["p_strike"].between(0, 1).all()
