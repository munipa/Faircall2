"""Synthetic season with planted leans; tests the bias logic only."""
import numpy as np
import pandas as pd

from analysis.bias import add_situation, lean, run
from models.baseline import BALL_RADIUS_FT, add_features, edge_distance_ft


def _season(n=30000, seed=3):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "game_pk": rng.integers(0, 300, n), "game_date": "2025-06-01", "game_type": "R",
        "at_bat_number": rng.integers(1, 70, n), "pitch_number": rng.integers(1, 7, n),
        "plate_x": rng.uniform(-1.4, 1.4, n), "plate_z": rng.uniform(1.0, 4.0, n),
        "sz_top": 3.4, "sz_bot": 1.6, "balls": rng.integers(0, 4, n),
        "strikes": rng.integers(0, 3, n), "stand": rng.choice(["L", "R"], n),
        "p_throws": rng.choice(["L", "R"], n), "inning_topbot": rng.choice(["Top", "Bot"], n),
        "pitch_type": rng.choice(["FF", "SL", "CH"], n), "fielder_2": rng.integers(1, 6, n),
    })
    df = df.drop_duplicates(["game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    logit = (-14 * (edge_distance_ft(df) - BALL_RADIUS_FT)
             + 1.0 * ((df["balls"] == 3) & (df["strikes"] == 0))   # bigger zone at 3-0
             + 0.8 * (df["fielder_2"] == 1))                         # catcher 1 frames well
    df["called_strike"] = (rng.random(len(df)) < 1 / (1 + np.exp(-logit))).astype("int8")
    df["description"] = np.where(df["called_strike"] == 1, "called_strike", "ball")
    return df


def test_situation_columns():
    df = add_situation(add_features(pd.DataFrame({
        "game_pk": [1, 1, 1], "at_bat_number": [1, 1, 1], "pitch_number": [1, 2, 4],
        "plate_x": [0.0, 1.2, 0.0], "plate_z": [2.5, 2.5, 3.6], "sz_top": 3.4, "sz_bot": 1.6,
        "balls": [0, 0, 1], "strikes": [0, 1, 1], "stand": "R", "p_throws": "R",
        "inning_topbot": ["Top", "Top", "Bot"], "called_strike": [1, 0, 0]})))
    assert df["previous_pitch"].tolist() == ["First pitch", "After a called strike",
                                             "After a swing or other"]
    assert df["batting_side"].tolist()[:2] == ["Away team batting"] * 2
    assert df.loc[1, "region"] == "Outside edge" and df.loc[2, "region"] == "Top edge"


def test_lean_math_and_interval():
    df = pd.DataFrame({"g": ["a"] * 400, "called_strike": [1] * 220 + [0] * 180, "p_loc": 0.5})
    row = lean(df, "g").iloc[0]
    assert row["extra_per_100"] == 5.0 and row["low"] < 5 < row["high"]


def test_run_finds_planted_count_and_catcher_leans(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    _season().to_parquet(raw / "statcast_2025_06.parquet")
    out = run(2025, model="logistic", raw_dir=raw, reports_dir=tmp_path / "rep", min_catcher=500)
    counts = out["counts"].set_index("count")
    assert counts.loc["3-0", "extra_per_100"] == counts["extra_per_100"].max()
    assert counts.loc["3-0", "clear"] == "more strikes"
    assert out["framing"].iloc[0]["fielder_2"] == 1
    text = (tmp_path / "rep" / "bias_2025.md").read_text()
    assert "## By count" in text and "Catcher framing" in text
