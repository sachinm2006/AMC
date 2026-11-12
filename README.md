# 🔋 Delhi DISCOM — Probabilistic Peak-Aware Load Forecasting & Procurement Copilot

> **CodeSpark 2026** · Domain 4, PS 2 · AMC Engineering College, Dept. of CSE - Data Science

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![LightGBM](https://img.shields.io/badge/LightGBM-Quantile-brightgreen)](https://lightgbm.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Problem Statement

Delhi DISCOM manages an extreme load swing — from **2,000 MW in winter** to **8,300 MW in peak summer**. Under-procuring power during a 45°C heatwave forces real-time Deviation Settlement Mechanism (DSM) purchases at **3.5× base tariff**. Over-procurement wastes 1× capacity charges.

This system predicts **P10/P50/P90 probabilistic load bands** 24–168 hours ahead and auto-generates an asymmetric procurement schedule that minimizes total expected ₹ cost.

---

## 🏗️ Architecture

```
Raw Delhi SLDC Data
        │
        ▼
┌───────────────────────┐
│  Module 1: Preprocessing │  ← Imputation, outlier clipping, continuous index
└───────────┬───────────┘
            │
            ▼
┌───────────────────────────────┐
│  Module 2: Feature Engineering │  ← CDH, thermal inertia, festival flags, lags
└───────────┬───────────────────┘
            │
            ▼
┌───────────────────────────────────────────┐
│  Module 3: Quantile Forecaster             │  ← LightGBM P10/P50/P90, XGBoost ensemble
│  Module 4: Peak-Event Classifier           │  ← Binary LightGBM (Recall > 85%)
│  Module 5: Walk-Forward Backtest (52 wins) │  ← Zero data leakage
└───────────┬───────────────────────────────┘
            │
            ▼
┌──────────────────────────────┐
│  Module 6: Procurement Advisor│  ← Asymmetric DSM cost optimizer
│  Module 7: Dashboard (Plotly) │  ← P10/P50/P90 bands + shock simulator
└──────────────────────────────┘
```

---

## 📁 Repository Structure

```
├── data/
│   ├── raw/                        ← Raw SLDC CSV / synthetic data
│   ├── generate_synthetic_data.py  ← Synthetic Delhi data generator
│   ├── clean_delhi_load.parquet    ← Cleaned output (auto-generated)
│   └── feature_matrix.parquet      ← Feature matrix (auto-generated)
├── src/
│   ├── preprocessing.py            ← Module 1: Data cleaning pipeline
│   ├── feature_engineering.py      ← Module 2: Feature builder
│   ├── train_models.py             ← Module 3 & 4: Quantile models + classifier
│   ├── backtest.py                 ← Module 5: Walk-forward evaluation
│   ├── procurement.py              ← Module 6: Asymmetric cost advisor
│   └── dashboard.py                ← Module 7: Plotly dashboard
├── models/                         ← Trained model pickles (auto-generated)
├── outputs/                        ← Predictions, metrics, plots (auto-generated)
├── run_phase1.py                   ← ✅ PHASE 1 runner (data + features)
├── run_phase2.py                   ← PHASE 2 runner (models + backtest)
├── run_all.py                      ← Full pipeline runner
├── requirements.txt
└── MODEL_CARD.md
```

---

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Phase 1 — Data Pipeline (using synthetic data)
```bash
python run_phase1.py
```

### 2b. Run Phase 1 with real SLDC data
```bash
python run_phase1.py --real path/to/delhi_sldc_hourly.csv
```

### 3. Run Phase 2 — Train Models + Backtest
```bash
python run_phase2.py
```

### 4. Launch Dashboard
```bash
python src/dashboard.py
```

---

## 📊 Key Metrics (Targets)

| Metric | Target |
|--------|--------|
| MAPE (P50 day-ahead) | < 5% vs. Seasonal-Naïve baseline |
| PICP (P10–P90 coverage) | ≈ 80% |
| Peak Timing Error | < 30 minutes average |
| Peak Magnitude Error | < 3% of peak MW |
| **Peak Recall** | **> 85% on top-decile events** |
| Pinball Loss | Minimized across P10/P50/P90 |

---

## 🧮 Asymmetric Procurement Formula

$$\text{Total Cost} = \sum \left[ \underbrace{U \times 3.5 \times T}_{\text{Under-procurement DSM}} + \underbrace{O \times 1.0 \times T}_{\text{Over-procurement waste}} \right]$$

Where *U* = under-procurement MW, *O* = over-procurement MW, *T* = base tariff (₹/MWh).

**Operating at P90 minimizes total expected financial loss.**

---

## 👥 Team

| Member | Role |
|--------|------|
| **Varun Kumar** | ML & Data Pipeline Lead |
| **Akshitha** | Backend API & Financial Logic Lead |
| **Member 3** | Frontend Dashboard & Pitch Lead |

---

## 🏆 Judge Alignment (Flipkart Minutes Persona)

Frame grid under-procurement as **dark-store inventory stockouts** and P90 tail-risk buffers as **safety-stock protection** during demand surge peaks. The asymmetric DSM penalty mirrors quick-commerce's asymmetric spoilage vs. stockout cost function.

---

*CodeSpark 2026 Hackathon · Department of CSE - Data Science · AMC Engineering College*
