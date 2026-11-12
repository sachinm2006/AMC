# -*- coding: utf-8 -*-
"""
Phase 2 Runner — Model Training & Walk-Forward Backtesting
=========================================================
Executes:
  1. Multi-horizon Quantile Regression models (P10/P50/P90 x 24h/168h)
  2. Binary Peak-Event Classifier
  3. Seasonal-Naive and Ridge Baselines
  4. 52-Window Rolling-Origin Walk-Forward Backtest
  5. Saves model pickles to models/ and predictions/metrics to outputs/
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from train_models import run_training
from backtest import run_backtest

def main():
    print("=" * 60)
    print("  CODESPARK 2026 | DOMAIN 4 PS 2 | PHASE 2 PIPELINE")
    print("  Model Training & Walk-Forward Validation — Varun Kumar")
    print("=" * 60)

    # 1. Train all models & generate predictions with bands
    print("\n>>> STEP 1: TRAINING QUANTILE MODELS & PEAK CLASSIFIER")
    metrics, models, preds = run_training()

    # 2. Run walk-forward backtest
    print("\n>>> STEP 2: RUNNING 52-WINDOW WALK-FORWARD BACKTEST")
    results_df, agg_df = run_backtest()

    print("\n" + "=" * 60)
    print("  PHASE 2 COMPLETE SUCCESSFULLY!")
    print("  Check models/ for saved .pkl files")
    print("  Check outputs/ for metrics, prediction bands, and plots")
    print("=" * 60)

if __name__ == "__main__":
    main()
