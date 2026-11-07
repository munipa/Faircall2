"""All pitches here are synthetic and test the logic only."""
import numpy as np
import pandas as pd
import pytest

from models.baseline import (BALL_RADIUS_FT, PLATE_HALF_WIDTH_FT, ZoneRule, add_features,
                             edge_distance_ft, in_zone, load_seasons, run)


def _pitches(**columns):
    base = {"plate_x": [0.0], "plate_z": [2.5], "sz_top": [3.5], "sz_bot": [1.5],
            "balls": [0], "strikes": [0], "stand": ["R"], "p_throws": ["R"]}
    return pd.DataFrame({**base, **columns})


def test_edge_distance_inside_outside_and_corner():
    df = _pitches(plate_x=[0.0, 1.0, PLATE_HALF_WIDTH_FT + 0.3],
                  plate_z=[2.5, 2.5, 3.5 + 0.4], sz_top=[3.5] * 3, sz_bot=[1.5] * 3,
                  balls=[0] * 3, strikes=[0] * 3, stand=["R"] * 3, p_throws=["R"] * 3)
    dist = edge_distance_ft(df)
    assert dist[0] < 0
    assert dist[1] == pytest.approx(1.0 - PLATE_HALF_WIDTH_FT)
    assert dist[2] == pytest.approx(0.5)   # 0.3-0.4-0.5 triangle at the corner


def test_ball_touching_the_edge_is_in_zone():
    edge = PLATE_HALF_WIDTH_FT + BALL_RADIUS_FT
    df = _pitches(plate_x=[edge - 0.001, edge + 0.001], plate_z=[2.5] * 2, sz_top=[3.5] * 2,
                  sz_bot=[1.5] * 2, balls=[0] * 2, strikes=[0] * 2, stand=["R"] * 2,
                  p_throws=["R"] * 2)
    assert in_zone(df).tolist() == [1, 0]


def test_x_batter_is_positive_inside_for_both_sides():
    # From the catcher's view a righty stands at negative x, a lefty at positive x.
    df = add_features(_pitches(plate_x=[-0.5, 0.5], plate_z=[2.5] * 2, sz_top=[3.5] * 2,
                               sz_bot=[1.5] * 2, balls=[0] * 2, strikes=[0] * 2,
                               stand=["R", "L"], p_throws=["R"] * 2))
    assert df["x_batter"].tolist() == [0.5, 0.5]


def test_zone_rule_uses_training_strike_rates():
    X = pd.DataFrame({"in_zone": [1, 1, 1, 1, 0, 0, 0, 0]})
    y = pd.Series([1, 1, 1, 0, 0, 0, 0, 1])
    p = ZoneRule().fit(X, y).predict_proba(pd.DataFrame({"in_zone": [1, 0]}))[:, 1]
    assert p.tolist() == [0.75, 0.25]


def test_missing_season_explains_how_to_fix(tmp_path):
    with pytest.raises(SystemExit, match="pipeline.ingest --season 2024"):
        load_seasons([2024], tmp_path)


def _synthetic_season(season, n, rng):
    sz_bot = rng.normal(1.6, 0.08, n)
    df = pd.DataFrame({
        "game_pk": rng.integers(1, 200, n) + season * 1000,
        "game_date": f"{season}-04-15", "game_type": "R",
        "at_bat_number": rng.integers(1, 80, n), "pitch_number": rng.integers(1, 8, n),
        "batter": rng.integers(1, 300, n), "pitcher": rng.integers(1, 300, n),
        "fielder_2": rng.integers(1, 40, n),
        "plate_x": rng.uniform(-1.6, 1.6, n), "plate_z": rng.uniform(0.8, 4.3, n),
        "sz_bot": sz_bot, "sz_top": sz_bot + rng.normal(1.8, 0.1, n),
        "balls": rng.integers(0, 4, n), "strikes": rng.integers(0, 3, n),
        "stand": rng.choice(["L", "R"], n), "p_throws": rng.choice(["L", "R"], n),
        "release_speed": rng.normal(92, 4, n), "pfx_x": rng.normal(0, 0.8, n),
        "pfx_z": rng.normal(1, 0.6, n),
    })
    df.loc[rng.random(n) < 0.01, "release_speed"] = np.nan
    # Umpires here shrink the zone with two strikes, plus some noise.
    logit = -14 * (edge_distance_ft(df) - BALL_RADIUS_FT) - 0.6 * (df["strikes"] == 2)
    df["called_strike"] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype("int8")
    df["description"] = np.where(df["called_strike"] == 1, "called_strike", "ball")
    return df


def test_end_to_end_on_synthetic_seasons(tmp_path):
    pytest.importorskip("xgboost")
    rng = np.random.default_rng(595)
    raw = tmp_path / "raw"
    raw.mkdir()
    _synthetic_season(2024, 6000, rng).to_parquet(raw / "statcast_2024_04.parquet")
    test = _synthetic_season(2025, 3000, rng)
    test.to_parquet(raw / "statcast_2025_04.parquet")

    metrics = run([2024], [2025], raw_dir=raw, reports_dir=tmp_path / "reports",
                  processed_dir=tmp_path / "processed")

    assert metrics["model"].tolist() == ["Zone rule", "Logistic regression", "XGBoost"]
    assert metrics[["accuracy", "auc", "brier"]].stack().between(0, 1).all()
    assert (metrics.set_index("model")["auc"] > 0.85).all()
    # Learned models should beat the zone rule's probabilities.
    loss = metrics.set_index("model")["log_loss"]
    assert loss["Logistic regression"] < loss["Zone rule"]
    assert loss["XGBoost"] < loss["Zone rule"]
    for name in ["baseline_metrics.md", "baseline_metrics.csv", "calibration.csv"]:
        assert (tmp_path / "reports" / name).exists()
    preds = pd.read_parquet(tmp_path / "processed" / "baseline_predictions_2025.parquet")
    assert len(preds) == len(test)
    assert {"p_zone_rule", "p_logistic_regression", "p_xgboost"} <= set(preds.columns)


def test_within_season_trains_before_and_tests_after_split(tmp_path):
    pytest.importorskip("xgboost")
    rng = np.random.default_rng(7)
    raw = tmp_path / "raw"
    raw.mkdir()
    season = _synthetic_season(2025, 6000, rng)
    season["game_date"] = rng.choice(["2025-05-10", "2025-06-10", "2025-08-10",
                                      "2025-09-10"], len(season))
    season.to_parquet(raw / "statcast_2025_05.parquet")

    metrics = run(within=2025, raw_dir=raw, reports_dir=tmp_path / "reports",
                  processed_dir=tmp_path / "processed")

    assert len(metrics) == 3
    assert (tmp_path / "reports" / "baseline_metrics_within_2025.md").exists()
    assert not (tmp_path / "reports" / "baseline_metrics.md").exists()
    preds = pd.read_parquet(tmp_path / "processed" / "baseline_predictions_within_2025.parquet")
    assert pd.to_datetime(preds["game_date"]).min() >= pd.Timestamp("2025-08-01")
    assert len(preds) == (pd.to_datetime(season["game_date"]) >= "2025-08-01").sum()


def test_split_date_with_no_test_games_is_rejected():
    from models.baseline import split_within_season
    df = pd.DataFrame({"game_date": ["2025-04-01", "2025-05-01"]})
    with pytest.raises(SystemExit, match="no training or no test"):
        split_within_season(df, "2025-12-01")


def test_overlapping_seasons_are_rejected(tmp_path):
    with pytest.raises(SystemExit, match="overlap"):
        run([2024], [2024], raw_dir=tmp_path)
