# AI Dev Log

| Date | Tool | Prompt / task | Outcome |
|---|---|---|---|
| 2026-11-05 | Claude Code | Planned project from proposal slides | Plan + repo scaffold |
| 2026-11-06 | Claude | Baseline called-strike models (zone rule, logistic regression, XGBoost) with tests | Tested on synthetic data, then run on real 2024-2025 data; added a within-season test after finding cross-season zone drift |
| 2026-11-07 | Claude | Umpire leaderboard: accuracy, close-pitch accuracy and extra strikes vs a cross-fitted model, with 95% intervals | Tested on synthetic data with a planted biased umpire, then run on real 2025 data (84 umpires rated) |
| 2026-11-20 | Claude | 2026 ABS challenge parser (pipeline/abs.py) and original-call restore in the leaderboard | Probed the real feed first; parser matched one game's box score 4/4; tested on synthetic feeds |
| 2026-11-20 | Claude | Multi-season trends report (analysis/trends.py); ABS report now validates our zone against ABS rulings and counts misses fixed | Run on real 2021-2026 data; our zone matched ABS rulings on 99.9% of challenged pitches |
