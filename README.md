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

## Status
Early development: project scaffold done, data pipeline next.

## AI tool usage
Logged in [`docs/AI_DEV_LOG.md`](docs/AI_DEV_LOG.md).
