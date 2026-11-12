# -*- coding: utf-8 -*-
"""
Phase 1 Runner -- End-to-End Pipeline
=====================================
Run this single script to execute the complete Phase 1:
  1. Generate synthetic Delhi load data (if real data not available)
  2. Preprocessing & cleaning
  3. Feature engineering
  4. Save all outputs + summary stats

Usage:
    python run_phase1.py                   # Uses synthetic data
    python run_phase1.py --real data/raw/my_data.csv   # Uses real SLDC CSV
"""

import argparse
import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from preprocessing import run_preprocessing
from feature_engineering import build_feature_matrix, FEATURE_COLS
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ─────────────────────────────────────────────────────────────────────────────
def generate_data_if_needed(raw_path: Path) -> None:
    if not raw_path.exists():
        print("Real data not found -- generating synthetic Delhi SLDC data...")
        # Add data directory to path so we can import generate_synthetic_data
        data_dir = Path(__file__).parent / "data"
        sys.path.insert(0, str(data_dir))
        from generate_synthetic_data import build_raw_dataset
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        df = build_raw_dataset()
        df.to_csv(raw_path)
        print(f"   ✅ Synthetic data saved → {raw_path}")
    else:
        print(f"   ✅ Using existing raw data → {raw_path}")


def plot_summary(df: pd.DataFrame, out_dir: Path) -> None:
    """Generate diagnostic plots for Phase 1 output."""
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    fig.suptitle("Phase 1 — Data Pipeline Summary (Delhi DISCOM)", fontsize=14, fontweight="bold")

    # Plot 1: Load time-series (first 2 months)
    sample = df["load_mw"].iloc[:24*60]
    axes[0].plot(sample.index, sample.values, linewidth=0.8, color="#1f77b4")
    axes[0].set_title("Hourly Load (MW) — First 60 Days")
    axes[0].set_ylabel("Load (MW)")
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Thermal features
    axes[1].plot(df["CDH"].resample("D").mean(), label="CDH (daily avg)", color="#d62728")
    axes[1].plot(df["rolling_temp_72h"].resample("D").mean(),
                 label="72h Rolling Temp", color="#ff7f0e", alpha=0.7)
    axes[1].set_title("Thermal Features")
    axes[1].set_ylabel("Value")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: Peak event distribution
    axes[2].hist(df["load_mw"], bins=80, color="#2ca02c", edgecolor="white", alpha=0.8)
    pct90 = df["load_mw"].quantile(0.90)
    axes[2].axvline(pct90, color="red", linestyle="--", linewidth=2,
                    label=f"P90 threshold: {pct90:.0f} MW")
    axes[2].set_title("Load Distribution + P90 Peak Threshold")
    axes[2].set_xlabel("Load (MW)")
    axes[2].set_ylabel("Frequency")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_dir / "phase1_summary.png", dpi=150, bbox_inches="tight")
    print(f"\n  📊 Summary plot saved → {out_dir / 'phase1_summary.png'}")
    plt.close()


def print_feature_stats(df: pd.DataFrame) -> None:
    available = [c for c in FEATURE_COLS if c in df.columns]
    print(f"\n{'─'*60}")
    print(f"  FEATURE MATRIX SUMMARY")
    print(f"{'─'*60}")
    print(f"  Shape         : {df.shape}")
    print(f"  Date range    : {df.index.min()} → {df.index.max()}")
    print(f"  Feature count : {len(available)}")
    print(f"  NaN in X      : {df[available].isna().sum().sum()}")
    print(f"  NaN in y      : {df['load_mw'].isna().sum()}")
    print(f"\n  Peak stats:")
    print(f"    P90 threshold : {df['peak_threshold_mw'].iloc[-1]:.1f} MW")
    print(f"    Peak hours    : {df['y_peak'].sum()} ({df['y_peak'].mean()*100:.1f}%)")
    print(f"\n  Load stats:")
    print(f"    Min : {df['load_mw'].min():.1f} MW")
    print(f"    Max : {df['load_mw'].max():.1f} MW")
    print(f"    Mean: {df['load_mw'].mean():.1f} MW")
    print(f"    Std : {df['load_mw'].std():.1f} MW")
    print(f"{'─'*60}")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Phase 1: Data Pipeline Runner")
    parser.add_argument("--real", type=str, default=None,
                        help="Path to real SLDC CSV (optional)")
    args = parser.parse_args()

    raw_path = Path(args.real) if args.real else Path("data/raw/delhi_load_raw.csv")

    print("=" * 60)
    print("  CODESPARK 2026 | DOMAIN 4 PS 2 | PHASE 1 PIPELINE")
    print("  Delhi DISCOM Load Forecasting — Varun Kumar")
    print("=" * 60)

    # Step 0: Generate or locate raw data
    generate_data_if_needed(raw_path)

    # Step 1: Preprocessing
    clean_df = run_preprocessing(raw_path=raw_path)

    # Step 2: Feature engineering
    feat_df = build_feature_matrix(clean_df)

    # Step 3: Save feature matrix
    feat_out = Path("data/feature_matrix.parquet")
    feat_df.to_parquet(feat_out)
    print(f"\n  ✅ Feature matrix saved → {feat_out}")

    # Step 4: Summary plots
    plot_summary(feat_df, Path("outputs"))

    # Step 5: Print stats
    print_feature_stats(feat_df)

    print("\n✅ PHASE 1 COMPLETE — Ready to hand off to model training (Phase 2)")
    print("   Next: python src/train_models.py")


if __name__ == "__main__":
    main()
