"""API tests against a small fake reports folder."""
import json

import pandas as pd
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    for season, acc in ((2024, 0.92), (2025, 0.93)):
        pd.DataFrame({"rank": [1, 2], "umpire_id": [7, 8], "umpire": ["Ump A", "Ump B"],
                      "games": 30, "pitches": 4000, "accuracy": [acc + 0.01, acc],
                      "accuracy_low": acc - 0.01, "accuracy_high": acc + 0.02,
                      "missed_per_game": [9.0, 10.0], "close_accuracy": 0.72,
                      "extra_strikes_per_100": [1.0, -1.0], "extra_low": [0.2, -1.8],
                      "extra_high": [1.8, -0.2]}).to_csv(tmp_path / f"umpire_leaderboard_{season}.csv", index=False)
    pd.DataFrame({"season": [2024, 2025], "accuracy": [0.92, 0.93], "missed_per_game": [11.0, 10.5],
                  "close_accuracy": [0.72, 0.73]}).to_csv(tmp_path / "trends.csv", index=False)
    (tmp_path / "challenge_advisor_2026.json").write_text(json.dumps({
        "overturn_rate": 0.54, "features": ["wrong_side_in", "strike_call", "two_strikes",
                                             "three_balls", "by_catcher", "by_pitcher"],
        "intercept": 0.0, "coefficients": {"wrong_side_in": 3.0, "strike_call": 0.0,
                                           "two_strikes": 0.0, "three_balls": 0.0,
                                           "by_catcher": 0.0, "by_pitcher": 0.0}}))
    monkeypatch.setenv("FAIRCALL_REPORTS", str(tmp_path))
    return TestClient(app)


def test_seasons_leaderboard_and_umpire_history(client):
    assert client.get("/api/seasons").json() == [2024, 2025]
    board = client.get("/api/leaderboard/2025").json()
    assert board[0]["umpire"] == "Ump A" and "accuracy" in board[0]
    ump = client.get("/api/umpires/7").json()
    assert [h["season"] for h in ump["history"]] == [2024, 2025]
    assert client.get("/api/leaderboard/1999").status_code == 404


def test_trends_framing_and_advisor(client):
    assert client.get("/api/trends").json()[-1]["season"] == 2025
    assert client.get("/api/framing/2025").status_code == 404     # not built yet
    wrong = client.get("/api/challenge/predict", params={"wrong_side_in": 1.5, "call": "strike"}).json()
    right = client.get("/api/challenge/predict", params={"wrong_side_in": -1.5, "call": "strike"}).json()
    assert wrong["recommend"] and not right["recommend"] and wrong["probability"] > 0.9
    assert client.get("/api/challenge/predict", params={"wrong_side_in": 1, "call": "x"}).status_code == 422


def test_home_page_serves(client):
    page = client.get("/")
    assert page.status_code == 200 and "FairCall" in page.text
