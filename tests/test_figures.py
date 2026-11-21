"""Figures render on synthetic data (the look is checked by eye, not here)."""
import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("xgboost")

from analysis.figures import abs_fixes, strike_zone  # noqa: E402
from tests.test_challenge_advisor import _season_with_challenges  # noqa: E402
from tests.test_bias import _season  # noqa: E402


def test_strike_zone_figure_and_count_areas(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    _season(n=30000).to_parquet(raw / "statcast_2025_06.parquet")
    out = strike_zone(2025, raw_dir=raw, reports_dir=tmp_path / "rep")
    assert out["path"].exists() and out["path"].stat().st_size > 10_000
    assert out["area"]["3-0"] > out["area"]["all"]       # the planted 3-0 lean shows up


def test_abs_fixes_figure(tmp_path):
    raw = _season_with_challenges(tmp_path)
    out = abs_fixes(2026, raw_dir=raw, reports_dir=tmp_path / "rep")
    assert out["path"].exists() and 0 < out["fixed"] <= out["misses"]
