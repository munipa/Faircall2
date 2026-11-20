"""Synthetic 2026 season with challenges; tests the advisor logic only."""
import json

import numpy as np
import pandas as pd

from analysis.challenge_advisor import predict, run
from models.baseline import BALL_RADIUS_FT, edge_distance_ft


def _season_with_challenges(tmp_path, n=20000, seed=5):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "game_pk": rng.integers(0, 200, n), "game_date": "2026-05-01", "game_type": "R",
        "at_bat_number": rng.integers(1, 70, n), "pitch_number": rng.integers(1, 7, n),
        "plate_x": rng.uniform(-1.3, 1.3, n), "plate_z": rng.uniform(1.1, 3.9, n),
        "sz_top": 3.3, "sz_bot": 1.6, "balls": rng.integers(0, 4, n), "strikes": rng.integers(0, 3, n),
        "stand": rng.choice(["L", "R"], n), "p_throws": "R",
        "inning_topbot": rng.choice(["Top", "Bot"], n), "home_team": "NYM", "away_team": "PHI",
        "pitch_type": "FF", "fielder_2": rng.integers(1, 4, n),
    }).drop_duplicates(["game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    edge = edge_distance_ft(df)
    truth = (edge <= BALL_RADIUS_FT).astype(int)                      # ABS zone
    umpire = (rng.random(len(df)) < 1 / (1 + np.exp(14 * (edge - BALL_RADIUS_FT)))).astype(int)
    near = np.abs(edge - BALL_RADIUS_FT) < 0.25
    challenged = near & (rng.random(len(df)) < 0.3)
    final = np.where(challenged, truth, umpire)                       # Statcast shows final call
    df["called_strike"] = final.astype("int8")
    df["description"] = np.where(final == 1, "called_strike", "ball")
    ch = df.loc[challenged, ["game_pk", "at_bat_number", "pitch_number"]].copy()
    ch["final_call"] = np.where(truth[challenged] == 1, "C", "B")
    ch["original_call"] = np.where(umpire[challenged] == 1, "C", "B")
    ch["is_overturned"] = ch["final_call"] != ch["original_call"]
    ch["challenger_role"] = rng.choice(["batter", "catcher", "pitcher"], len(ch), p=[.45, .5, .05])
    raw = tmp_path / "raw"
    raw.mkdir()
    df.to_parquet(raw / "statcast_2026_05.parquet")
    ch.to_parquet(raw / "abs_challenges_2026.parquet")
    return raw


def test_advisor_learns_from_location_and_saves_a_usable_model(tmp_path):
    raw = _season_with_challenges(tmp_path)
    result = run(2026, raw_dir=raw, reports_dir=tmp_path / "rep")
    assert result["metrics"]["auc"] > 0.9
    assert result["metrics"]["brier"] < result["metrics"]["brier_baseline"]

    model = json.loads((tmp_path / "rep" / "challenge_advisor_2026.json").read_text())
    wrong = predict(model, 2.0, strike_call=True)
    right = predict(model, -2.0, strike_call=True)
    assert wrong > 0.8 and right < 0.2

    text = (tmp_path / "rep" / "challenge_advisor_2026.md").read_text()
    for heading in ("## Overturn rate by where the pitch was", "## Missed opportunities", "## Teams"):
        assert heading in text
