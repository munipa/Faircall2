# Baseline called-strike models

Trained on 2024, tested on 2025.
Training pitches: 366,873. Test pitches: 368,845.
Test called-strike rate: 0.313.
Blocked balls: included.

| Model | Accuracy | AUC | Log loss | Brier |
|---|---|---|---|---|
| Zone rule | 0.9290 | 0.9215 | 0.2483 | 0.0648 |
| Logistic regression | 0.9337 | 0.9831 | 0.1578 | 0.0483 |
| XGBoost | 0.9395 | 0.9867 | 0.1403 | 0.0433 |

Higher accuracy and AUC are better. Lower log loss and Brier are better.
The models predict the umpire's call, not whether the call was correct.
