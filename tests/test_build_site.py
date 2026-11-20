"""Builds the static site from a small fake reports folder."""
import json

import pandas as pd
import pytest

pytest.importorskip("fastapi")
from scripts.build_site import build  # noqa: E402


def test_build_writes_static_site(tmp_path, monkeypatch):
    rep = tmp_path / "reports"
    rep.mkdir()
    pd.DataFrame({"rank": [1], "umpire_id": [7], "umpire": ["Ump A"], "games": [30], "pitches": [4000],
                  "accuracy": [0.93], "missed_per_game": [10.0]}).to_csv(rep / "umpire_leaderboard_2025.csv", index=False)
    pd.DataFrame({"season": [2025], "accuracy": [0.93], "missed_per_game": [10.0],
                  "close_accuracy": [0.73]}).to_csv(rep / "trends.csv", index=False)
    monkeypatch.setenv("FAIRCALL_REPORTS", str(rep))

    out = tmp_path / "docs"
    (out).mkdir()
    (out / "AI_DEV_LOG.md").write_text("keep me")
    built = build(out)

    assert built["seasons"] == [2025] and built["trends.json"] and not built["advisor.json"]
    assert json.loads((out / "data" / "umpires.json").read_text())["7"]["umpire"] == "Ump A"
    page = (out / "index.html").read_text()
    assert "window.FAIRCALL_STATIC = true" in page
    assert (out / "AI_DEV_LOG.md").read_text() == "keep me"      # other docs untouched
