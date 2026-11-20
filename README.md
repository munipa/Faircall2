# FairCall

Auditing the MLB strike zone with machine learning.
CPE 595 · Applied Machine Learning · Akhil Munipalli, Hugh O'Donnell, Soham Panigrahi

## What it does
Umpires miss 10+ ball/strike calls per game, and the errors are skewed in predictable ways (two-strike counts, zone edges). FairCall:

1. **Learns the zone**: predicts the probability a pitch is called a strike from location, batter zone, count and pitch traits.
2. **Isolates bias**: separates systematic bias from noise, with confidence intervals on every metric.
3. **Explains it**: an LLM turns the metrics into plain-language umpire report cards, game recaps and an ABS challenge advisor.

Results are framed as consistency audits, not judgments of individual umpires.

## Pipeline
Statcast pitch data → called-strike model → bias and consistency engine → FairCall web app

## Repo layout
| Folder | Purpose |
|---|---|
| `pipeline/` | Ingest and clean Statcast, umpire and ABS data |
| `models/` | Called-strike models (logistic regression, XGBoost, PyTorch) |
| `analysis/` | Bias and consistency metrics |
| `api/` | FastAPI backend |
| `llm/` | Report card generation |
| `web/` | React front end |
| `data/` | Raw and processed data (git-ignored) |
| `docs/` | AI dev log and reports |
| `tests/` | Tests |

## Tech stack
pybaseball, MLB Stats API, scikit-learn, XGBoost, PyTorch, OpenAI API, FastAPI, React.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Put API keys in a `.env` file (git-ignored). Never commit them.

## Baseline model
Train on 2024 and test on 2025 (download both seasons with `pipeline.ingest` first):
```bash
python -m models.baseline              # train 2024, test 2025
python -m models.baseline --within 2025  # train Apr-Jul 2025, test Aug-Sep 2025
```
Compares a zone rule, logistic regression and XGBoost. Results go to `reports/`
(metrics table and calibration chart) and test-set predictions to `data/processed/`.

## Umpire leaderboard
Accuracy and strike-calling tendencies for each home-plate umpire in one season:
```bash
python -m pipeline.umpires --season 2025
python -m analysis.umpire_stats --season 2025
```
Writes `reports/umpire_leaderboard_<season>.md`, `.csv` and `.png`. Expected strikes come
from the XGBoost baseline cross-fitted within the season, and every metric has a 95% interval.

## 2026 ABS challenges
Statcast records the call after an ABS challenge. This recovers the umpire's original call
on every challenged pitch from the MLB Stats API game feed and reports how challenges went:
```bash
python -m pipeline.abs --season 2026
python -m analysis.umpire_stats --season 2026   # uses the original calls
```
Writes `data/raw/abs_challenges_2026.parquet` and `reports/abs_challenges_2026.md`.

## Trends across seasons
League accuracy by season, Statcast's zone measurements, and whether umpire accuracy
carries over from one season to the next:
```bash
python -m analysis.trends
```
Writes `reports/trends.md` and `reports/trends.png`.

## Bias breakdowns
Where umpires lean beyond location: by count, previous pitch, home or away,
handedness, pitch type, zone region, plus catcher framing:
```bash
python -m analysis.bias --season 2025 --catcher-names
```

## Challenge advisor
How likely an ABS challenge is to be overturned, which misses teams left unchallenged,
and a saved model for the app:
```bash
python -m analysis.challenge_advisor --season 2026
```

## App
FastAPI backend plus a single web page (leaderboard, umpire histories, trends,
catcher framing, challenge advisor). Run the analyses first, then:
```bash
uvicorn api.main:app --reload
```
and open http://127.0.0.1:8000

## Status
Data for 2021-2026, baseline model, umpire leaderboards for every season, 2026 ABS challenges and multi-season trends done. Bias breakdowns, challenge advisor and an app prototype done. LLM report cards, PyTorch comparison and deployment next.

## AI tool usage
Logged in [`docs/AI_DEV_LOG.md`](docs/AI_DEV_LOG.md).
