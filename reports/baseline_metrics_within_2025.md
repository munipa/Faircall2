# Baseline called-strike models

Trained on 2025 games before 2025-08-01, tested on 2025 games from 2025-08-01 on.
Training pitches: 247,397. Test pitches: 121,448.
Test called-strike rate: 0.313.
Blocked balls: included.

| Model | Accuracy | AUC | Log loss | Brier |
|---|---|---|---|---|
| Zone rule | 0.9295 | 0.9225 | 0.2451 | 0.0642 |
| Logistic regression | 0.9362 | 0.9830 | 0.1553 | 0.0471 |
| XGBoost | 0.9411 | 0.9865 | 0.1382 | 0.0424 |

Higher accuracy and AUC are better. Lower log loss and Brier are better.
The models predict the umpire's call, not whether the call was correct.
