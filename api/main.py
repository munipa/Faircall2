"""FairCall API: serves the precomputed reports and the challenge advisor.

Run:
    uvicorn api.main:app --reload
then open http://127.0.0.1:8000

Reads the files the analysis scripts write to reports/ (set FAIRCALL_REPORTS to
use another folder): umpire_leaderboard_<season>.csv, catcher_framing_<season>.csv,
trends.csv and challenge_advisor_<season>.json.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "index.html"

app = FastAPI(title="FairCall", description="Auditing the MLB strike zone")


def reports_dir() -> Path:
    return Path(os.environ.get("FAIRCALL_REPORTS", ROOT / "reports"))


def _records(df: pd.DataFrame) -> list[dict]:
    out = df.to_dict(orient="records")
    return [{k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in r.items()}
            for r in out]


def _board(season: int) -> pd.DataFrame:
    path = reports_dir() / f"umpire_leaderboard_{season}.csv"
    if not path.exists():
        raise HTTPException(404, f"no leaderboard for {season}")
    return pd.read_csv(path)


@app.get("/api/seasons")
def seasons() -> list[int]:
    found = [int(m.group(1)) for p in reports_dir().glob("umpire_leaderboard_*.csv")
             if (m := re.fullmatch(r"umpire_leaderboard_(\d{4})\.csv", p.name))]
    return sorted(found)


LEADERBOARD_COLUMNS = ["rank", "umpire_id", "umpire", "games", "pitches", "accuracy",
                       "accuracy_low", "accuracy_high", "missed_per_game", "close_accuracy",
                       "extra_strikes_per_100", "extra_low", "extra_high",
                       "two_strike_extra_per_100", "three_ball_extra_per_100"]


@app.get("/api/leaderboard/{season}")
def leaderboard(season: int) -> list[dict]:
    board = _board(season)
    return _records(board[[c for c in LEADERBOARD_COLUMNS if c in board]])


@app.get("/api/umpires/{umpire_id}")
def umpire(umpire_id: int) -> dict:
    history = []
    for season in seasons():
        row = _board(season)
        row = row[row["umpire_id"] == umpire_id]
        if len(row):
            history.append({"season": season, **_records(row[[c for c in LEADERBOARD_COLUMNS
                                                               if c in row]])[0]})
    if not history:
        raise HTTPException(404, "umpire not found")
    return {"umpire_id": umpire_id, "umpire": history[-1]["umpire"], "history": history}


@app.get("/api/trends")
def trends() -> list[dict]:
    path = reports_dir() / "trends.csv"
    if not path.exists():
        raise HTTPException(404, "run: python -m analysis.trends")
    return _records(pd.read_csv(path))


@app.get("/api/framing/{season}")
def framing(season: int) -> list[dict]:
    path = reports_dir() / f"catcher_framing_{season}.csv"
    if not path.exists():
        raise HTTPException(404, f"run: python -m analysis.bias --season {season}")
    df = pd.read_csv(path)
    return _records(df[[c for c in ["catcher", "pitches", "extra_per_100", "low", "high", "clear"]
                        if c in df]])


def _advisor(season: int = 2026) -> dict:
    path = reports_dir() / f"challenge_advisor_{season}.json"
    if not path.exists():
        raise HTTPException(404, "run: python -m analysis.challenge_advisor --season 2026")
    return json.loads(path.read_text())


@app.get("/api/challenge/predict")
def challenge_predict(
        wrong_side_in: float = Query(..., ge=-12, le=12,
                                     description="inches on the wrong side for the call; "
                                                 "negative = the call looks right"),
        call: str = Query(..., pattern="^(strike|ball)$"),
        balls: int = Query(0, ge=0, le=3), strikes: int = Query(0, ge=0, le=2),
        challenger: str = Query("batter", pattern="^(batter|catcher|pitcher)$")) -> dict:
    from analysis.challenge_advisor import predict

    model = _advisor()
    p = predict(model, wrong_side_in, call == "strike", balls, strikes, challenger)
    return {"probability": round(p, 4), "recommend": p >= 0.5,
            "league_overturn_rate": model.get("overturn_rate")}


@app.get("/")
def home():
    return FileResponse(WEB)
