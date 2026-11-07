"""Baseline called-strike models: a zone rule, logistic regression and XGBoost.

Each model predicts the umpire's call (called_strike = 1 or 0) for a taken pitch.
The zone rule needs no learning and is the bar the other two must beat.

Usage:
    python -m models.baseline                                # train 2024, test 2025
    python -m models.baseline --train 2023 2024 --test 2025
    python -m models.baseline --drop-blocked                 # leave out blocked balls
    python -m models.baseline --within 2025                  # train Apr-Jul, test Aug-Sep
    python -m models.baseline --within 2025 --split-date 2025-07-01

Cross-season testing shows how the model holds up when Statcast's zone
measurement changes between years. Within-season testing keeps that measurement
the same, so it shows the model's accuracy on its own.

Reads:  data/raw/statcast_<season>_*.parquet (from pipeline.ingest)
Writes: reports/baseline_metrics<tag>.md and .csv, reports/calibration<tag>.csv
        and .png, data/processed/baseline_predictions_<tag>.parquet, where the
        tag is empty for cross-season runs and _within_<season> otherwise.
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

TARGET = "called_strike"
PLATE_HALF_WIDTH_FT = 17 / 2 / 12   # half of the 17-inch plate
BALL_RADIUS_FT = 1.45 / 12          # a pitch is in if any part of the ball touches the zone
LOCATION = ["plate_x", "plate_z", "sz_top", "sz_bot", "balls", "strikes", "stand"]

LOGISTIC_FEATURES = ["edge_dist", "abs_x", "abs_x_sq", "z_norm", "z_center_sq",
                     "x_batter", "balls", "strikes", "stand_L"]
XGB_FEATURES = ["plate_x", "plate_z", "sz_top", "sz_bot", "z_norm", "x_batter", "edge_dist",
                "balls", "strikes", "stand_L", "p_throws_L",
                "release_speed", "pfx_x", "pfx_z"]


# ---------------------------------------------------------------- zone geometry

def edge_distance_ft(df: pd.DataFrame) -> np.ndarray:
    """Distance from the ball's center to the nearest zone edge, in feet.

    Negative inside the zone, positive outside. Outside a corner it is the
    diagonal distance to that corner.
    """
    dx = df["plate_x"].abs().to_numpy() - PLATE_HALF_WIDTH_FT
    dz = np.maximum(df["sz_bot"] - df["plate_z"], df["plate_z"] - df["sz_top"]).to_numpy()
    outside = np.hypot(np.maximum(dx, 0), np.maximum(dz, 0))
    inside = np.maximum(dx, dz)
    return np.where((dx > 0) | (dz > 0), outside, inside)


def in_zone(df: pd.DataFrame) -> np.ndarray:
    return (edge_distance_ft(df) <= BALL_RADIUS_FT).astype(int)


# ---------------------------------------------------------------- data

def load_seasons(seasons: list[int], raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    frames = []
    for season in seasons:
        files = sorted(glob.glob(str(raw_dir / f"statcast_{season}_*.parquet")))
        if not files:
            raise SystemExit(f"no statcast_{season}_*.parquet files in {raw_dir}; "
                             f"run: python -m pipeline.ingest --season {season}")
        frames += [pd.read_parquet(f) for f in files]
    df = pd.concat(frames, ignore_index=True)
    df = df.dropna(subset=LOCATION + [TARGET])
    return df[df["sz_top"] > df["sz_bot"]].reset_index(drop=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["z_norm"] = (out["plate_z"] - out["sz_bot"]) / (out["sz_top"] - out["sz_bot"])
    out["z_center_sq"] = (out["z_norm"] - 0.5) ** 2
    out["abs_x"] = out["plate_x"].abs()
    out["abs_x_sq"] = out["abs_x"] ** 2
    out["edge_dist"] = edge_distance_ft(out)
    out["in_zone"] = in_zone(out)
    out["stand_L"] = (out["stand"] == "L").astype(int)
    out["p_throws_L"] = (out.get("p_throws") == "L").astype(int)
    # plate_x is from the catcher's view. Flip it so positive always means inside to the batter.
    out["x_batter"] = np.where(out["stand"] == "R", -out["plate_x"], out["plate_x"])
    for column in ("release_speed", "pfx_x", "pfx_z"):
        if column not in out:
            out[column] = np.nan   # XGBoost handles missing values
    return out


# ---------------------------------------------------------------- models

class ZoneRule:
    """Predicts the training-set strike rate for pitches in or out of the measured zone."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "ZoneRule":
        rates = pd.Series(np.asarray(y)).groupby(X["in_zone"].to_numpy()).mean()
        self.rates_ = {0: float(rates.get(0, 0.0)), 1: float(rates.get(1, 1.0))}
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = X["in_zone"].map(self.rates_).to_numpy(dtype=float)
        return np.column_stack([1 - p, p])


def make_models(seed: int = 595) -> dict:
    from xgboost import XGBClassifier

    return {
        "Zone rule": (ZoneRule(), ["in_zone"]),
        "Logistic regression": (
            make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
            LOGISTIC_FEATURES),
        "XGBoost": (
            # min_child_weight and reg_lambda keep it from overfitting small samples.
            XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                          min_child_weight=20, reg_lambda=5.0,
                          subsample=0.8, colsample_bytree=0.8, eval_metric="logloss",
                          n_jobs=-1, random_state=seed),
            XGB_FEATURES),
    }


def evaluate(y: pd.Series, p: np.ndarray) -> dict:
    return {
        "accuracy": accuracy_score(y, (p >= 0.5).astype(int)),
        "auc": roc_auc_score(y, p),
        "log_loss": log_loss(y, np.clip(p, 1e-6, 1 - 1e-6), labels=[0, 1]),
        "brier": brier_score_loss(y, p),
    }


# ---------------------------------------------------------------- outputs

def _slug(name: str) -> str:
    return name.lower().replace(" ", "_")


def _markdown(metrics: pd.DataFrame, info: dict) -> str:
    lines = ["# Baseline called-strike models", "",
             f"Trained on {info['train']}, tested on {info['test']}.",
             f"Training pitches: {info['n_train']:,}. Test pitches: {info['n_test']:,}.",
             f"Test called-strike rate: {info['strike_rate']:.3f}.",
             f"Blocked balls: {'excluded' if info['drop_blocked'] else 'included'}.", "",
             "| Model | Accuracy | AUC | Log loss | Brier |", "|---|---|---|---|---|"]
    for row in metrics.itertuples(index=False):
        lines.append(f"| {row.model} | {row.accuracy:.4f} | {row.auc:.4f} | "
                     f"{row.log_loss:.4f} | {row.brier:.4f} |")
    lines += ["", "Higher accuracy and AUC are better. Lower log loss and Brier are better.",
              "The models predict the umpire's call, not whether the call was correct."]
    return "\n".join(lines) + "\n"


def _plot_calibration(calibration: pd.DataFrame, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping calibration.png")
        return False
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], color="#999999", linestyle="--", linewidth=1, label="Perfect")
    for name, group in calibration.groupby("model", sort=False):
        ax.plot(group["predicted"], group["actual"], marker="o", markersize=4, label=name)
    ax.set_xlabel("Predicted strike probability")
    ax.set_ylabel("Actual called-strike rate")
    ax.set_title("Calibration on the test season")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


# ---------------------------------------------------------------- main

def split_within_season(df: pd.DataFrame, split_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Games before split_date train the model; games on or after it test it."""
    dates = pd.to_datetime(df["game_date"])
    cutoff = pd.Timestamp(split_date)
    train, test = df[dates < cutoff], df[dates >= cutoff]
    if train.empty or test.empty:
        raise SystemExit(f"split date {split_date} leaves no training or no test pitches")
    return train, test


def run(train_seasons: list[int] | None = None, test_seasons: list[int] | None = None, *,
        within: int | None = None, split_date: str | None = None,
        raw_dir: Path = RAW_DIR, reports_dir: Path = REPORTS_DIR,
        processed_dir: Path = PROCESSED_DIR, drop_blocked: bool = False,
        seed: int = 595) -> pd.DataFrame:
    if within is not None:
        split_date = split_date or f"{within}-08-01"
        train, test = split_within_season(add_features(load_seasons([within], raw_dir)),
                                          split_date)
        train_label = f"{within} games before {split_date}"
        test_label = f"{within} games from {split_date} on"
        tag, pred_tag = f"_within_{within}", f"within_{within}"
    else:
        train_seasons, test_seasons = train_seasons or [2024], test_seasons or [2025]
        if set(train_seasons) & set(test_seasons):
            raise SystemExit("train and test seasons must not overlap")
        train = add_features(load_seasons(train_seasons, raw_dir))
        test = add_features(load_seasons(test_seasons, raw_dir))
        train_label = ", ".join(map(str, train_seasons))
        test_label = ", ".join(map(str, test_seasons))
        tag, pred_tag = "", "_".join(map(str, test_seasons))
    if drop_blocked:
        train = train[train["description"] != "blocked_ball"]
        test = test[test["description"] != "blocked_ball"]

    keep = [c for c in ["game_pk", "game_date", "at_bat_number", "pitch_number", "batter",
                        "pitcher", "fielder_2", "balls", "strikes", TARGET, "in_zone",
                        "edge_dist"] if c in test]
    predictions = test[keep].copy()
    rows, curves = [], []
    for name, (model, columns) in make_models(seed).items():
        print(f"training {name} on {len(train):,} pitches ...")
        model.fit(train[columns], train[TARGET])
        p = model.predict_proba(test[columns])[:, 1]
        predictions[f"p_{_slug(name)}"] = p
        rows.append({"model": name, **evaluate(test[TARGET], p)})
        actual, predicted = calibration_curve(test[TARGET], p, n_bins=10)
        curves.append(pd.DataFrame({"model": name, "predicted": predicted, "actual": actual}))
    metrics = pd.DataFrame(rows)
    calibration = pd.concat(curves, ignore_index=True)

    reports_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    info = {"train": train_label, "test": test_label,
            "n_train": len(train), "n_test": len(test),
            "strike_rate": float(test[TARGET].mean()), "drop_blocked": drop_blocked}
    metrics.to_csv(reports_dir / f"baseline_metrics{tag}.csv", index=False)
    calibration.to_csv(reports_dir / f"calibration{tag}.csv", index=False)
    (reports_dir / f"baseline_metrics{tag}.md").write_text(_markdown(metrics, info))
    _plot_calibration(calibration, reports_dir / f"calibration{tag}.png")
    predictions.to_parquet(processed_dir / f"baseline_predictions_{pred_tag}.parquet",
                           index=False)

    print("\n" + _markdown(metrics, info))
    return metrics


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--train", type=int, nargs="+", default=[2024])
    p.add_argument("--test", type=int, nargs="+", default=[2025])
    p.add_argument("--within", type=int, help="train and test inside this one season")
    p.add_argument("--split-date", help="YYYY-MM-DD for --within (default Aug 1)")
    p.add_argument("--drop-blocked", action="store_true", help="leave out blocked balls")
    a = p.parse_args()
    run(a.train, a.test, within=a.within, split_date=a.split_date,
        drop_blocked=a.drop_blocked)


if __name__ == "__main__":
    main()
