"""Synthetic seasons; tests the trend logic only."""
import numpy as np
import pandas as pd

from analysis.trends import available_seasons, run


def _season(season, n, miss_rate, rng):
    df = pd.DataFrame({
        "game_pk": rng.integers(0, 50, n) + season * 100, "game_date": f"{season}-05-01",
        "plate_x": rng.uniform(-1.5, 1.5, n), "plate_z": rng.uniform(1, 4, n),
        "sz_top": 3.4, "sz_bot": 1.6, "balls": 0, "strikes": 0, "stand": "R", "p_throws": "R",
    })
    inside = (df["plate_x"].abs() <= 0.83) & df["plate_z"].between(1.48, 3.52)
    flip = rng.random(n) < miss_rate
    df["called_strike"] = (inside ^ flip).astype("int8")
    return df


def test_trends_summarize_each_season_and_persistence(tmp_path):
    rng = np.random.default_rng(1)
    raw, reports = tmp_path / "raw", tmp_path / "reports"
    raw.mkdir()
    reports.mkdir()
    _season(2024, 4000, 0.10, rng).to_parquet(raw / "statcast_2024_05.parquet")
    _season(2025, 4000, 0.05, rng).to_parquet(raw / "statcast_2025_05.parquet")
    for s, shift in ((2024, 0.0), (2025, 0.001)):
        pd.DataFrame({"umpire_id": range(10), "accuracy": np.linspace(0.9, 0.95, 10) + shift,
                      "close_accuracy": 0.7, "extra_strikes_per_100": np.linspace(-2, 2, 10)}
                     ).to_csv(reports / f"umpire_leaderboard_{s}.csv", index=False)

    assert available_seasons(raw) == [2024, 2025]
    summary = run(raw_dir=raw, reports_dir=reports)

    assert summary["season"].tolist() == [2024, 2025]
    assert summary.loc[0, "missed_per_game"] > summary.loc[1, "missed_per_game"]
    text = (reports / "trends.md").read_text()
    assert "Is umpire accuracy a stable trait?" in text and "| 2024→2025 | 10 | 1.00 |" in text
