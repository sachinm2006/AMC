# 🔋 Delhi DISCOM -- Probabilistic Peak-Aware Load Forecasting & Procurement Copilot

> **🌐 Live website:** [Open LoadIQ](https://probabilistic-peak-aware-load-forec.vercel.app/)

> **CodeSpark 2026** · Domain 4, PS 2 · AMC Engineering College, Dept. of CSE - Data Science  
> **Team Lead / ML Lead:** Varun Kumar

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.0-61DAFB)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8.0-646CFF)](https://vitejs.dev)
[![LightGBM](https://img.shields.io/badge/LightGBM-Quantile-brightgreen)](https://lightgbm.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 Executive Problem Statement & Commercial Impact

Delhi DISCOM manages one of the most volatile electricity grids in India -- swinging from **2,000 MW in winter** to an all-time record of **8,656 MW in peak summer**. 

Power purchase accounts for **75% to 80% (Rs. 25,000 to Rs. 30,000 Crore)** of total annual expenditure. Under **DERC (Delhi Electricity Regulatory Commission) regulations**, power purchase costs are passed through via consumer surcharges (FPPAS), **BUT avoidable Deviation Settlement Mechanism (DSM) penalties caused by scheduling errors are strictly DISALLOWED in annual true-ups**. DSM penalties directly destroy operating profit and shareholder equity.

Under **CERC DSM 2024 regulations**, under-procuring power during a severe heatwave incurs emergency Real-Time Market (RTM) charges up to Rs. 10/unit plus frequency penalty multipliers reaching **150% to 200% (Rs. 12 to Rs. 15/unit, a 3.5x penalty multiple)**. Over-procurement wastes 1.0x capacity fixed charges.

### Key Performance Benchmarks (52-Window Rolling-Origin Backtest)
* **Day-Ahead P50 Pooled MAPE:** **4.18%** (vs 7.18% Seasonal-Naïve and 5.86% Yesterday-Naïve -- a **41.8% error reduction**).
* **Peak Hours Recall:** **96.9%** with **85.1% Precision** ($F_1 = 0.906$) at asymmetric cost threshold $p^* = 0.222$.
* **Conformal Coverage (CQR PICP):** **81.1%** empirical confidence coverage (surpassing the 80% regulatory threshold).
* **Net P&L Savings:** Avoids **Rs. 206.66 Crore** in catastrophic unhedged DSM penalties across 8,736 operating hours.

---

## 🏗️ Clean Modular Repository Architecture

```
Probabilistic-Peak-Aware-Load-Forecasting-Procurement-Copilot/
├── backend/                  # FastAPI REST API & Copilot Decision Engine
│   ├── main.py               # 13 REST API endpoints (forecast, peaks, copilot, risk)
│   ├── copilot.py            # Natural language dispatch desk risk insights
│   ├── peak_analytics.py     # Extreme event distribution analytics
│   ├── metrics.py            # MAE, RMSE, MAPE evaluation metrics
│   └── procurement.py        # Asymmetric procurement financial simulator
│
├── frontend/                 # Peakwise React 19 + TypeScript + Vite Dashboard
│   ├── src/                  # App.tsx, Dashboard.tsx, Tailwind & Recharts components
│   ├── package.json          # Node dependencies (React 19, Lucide, Recharts)
│   └── vite.config.ts        # Vite configuration
│
├── models/                   # Serialized Production ML Models
│   ├── lgbm_q10_h24.pkl      # Day-ahead 10th percentile quantile regressor
│   ├── lgbm_q50_h24.pkl      # Day-ahead 50th percentile (median) regressor
│   ├── lgbm_q90_h24.pkl      # Day-ahead 90th percentile quantile regressor
│   ├── lgbm_q10_h168.pkl     # Week-ahead 10th percentile regressor
│   ├── lgbm_q50_h168.pkl     # Week-ahead 50th percentile regressor
│   ├── lgbm_q90_h168.pkl     # Week-ahead 90th percentile regressor
│   ├── lgbm_peak_classifier.pkl # Binary peak classifier (96.9% Recall)
│   ├── ridge_h24.pkl         # Linear L2 benchmark model
│   └── MODEL_CARD.md         # Production model card & performance specifications
│
├── data/                     # Data Pipeline & Feature Store
│   ├── raw/                  # Raw SLDC load & weather inputs
│   ├── clean_delhi_load.parquet # 3-year cleaned hourly load series
│   ├── feature_matrix.parquet # 47 domain features (26,112 rows x 53 cols)
│   └── generate_synthetic_data.py # Synthetic data generation engine
│
├── src/                      # Core ML Pipelines & Conformal Inference
│   ├── preprocessing.py      # Outlier clipping & missing value imputation
│   ├── feature_engineering.py # 47 features (thermal inertia, CDH, heatwave onset)
│   ├── train_models.py       # Multi-horizon quantile LightGBM training
│   ├── backtest.py           # 52-window rolling-origin walk-forward CQR backtest
│   ├── error_diagnostics.py  # SHAP values, heatwave onset & missed peak analysis
│   └── procurement.py        # Financial loss function & procurement optimizer
│
├── outputs/                  # Backtest Artifacts & Visualizations
│   ├── backtest_summary.csv  # 52-fold pooled backtest metrics
│   ├── rupee_procurement_impact.csv # Rs. 206.66 Cr savings financial matrix
│   ├── error_heatmap.png     # Hour-of-day vs month error density heatmap
│   ├── shap_summary.png      # SHAP feature importance impact
│   └── heatwave_onset_analysis.png # Heatwave onset buffer response curve
│
├── docs/                     # Executive Reports & Presentation Guides
│   ├── Delhi_DISCOM_PL_and_Pitch_Master_Guide.pdf # 5-Page P&L & 10-Slide Deck Guide
│   ├── Delhi_DISCOM_Project_Master_Technical_Report.pdf # 5-Page Technical ML Dossier
│   └── ui-ux-plan.md         # UI/UX design specifications
│
├── run_local.py              # Unified localhost launcher (Backend + Frontend)
├── run_phase1.py             # Phase 1 data cleaning & feature generation runner
├── run_phase2.py             # Phase 2 model training & evaluation runner
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 🚀 How to Run on Localhost

### 1. Unified Launcher (Runs Both Backend & Frontend)
```bash
# Clone the repository
git clone https://github.com/sachinm2006/Probabilistic-Peak-Aware-Load-Forecasting-Procurement-Copilot.git
cd Probabilistic-Peak-Aware-Load-Forecasting-Procurement-Copilot

# Install Python requirements
pip install -r requirements.txt

# Start both servers together
python run_local.py
```
* **FastAPI Backend:** [http://localhost:8000](http://localhost:8000)
* **Swagger API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **React Dashboard UI:** [http://localhost:5173](http://localhost:5173)

---

### 2. Running Services Individually

#### Option A: Run FastAPI Backend Only
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Test endpoints:
* Root health check: `GET http://127.0.0.1:8000/`
* Latest 24h forecast bands: `GET http://127.0.0.1:8000/api/forecast`
* Peak alert status: `GET http://127.0.0.1:8000/api/peaks`
* Copilot natural language insights: `GET http://127.0.0.1:8000/api/copilot`
* Asymmetric procurement comparison: `GET http://127.0.0.1:8000/api/procurement/comparison`

#### Option B: Run React Frontend Only
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in any browser.

---

## 📊 ML Pipeline Reproduction

```bash
# Phase 1: Build 47 domain features from raw SLDC load
python run_phase1.py

# Phase 2: Train multi-horizon LightGBM quantiles & peak classifier
python run_phase2.py

# Run 52-window rolling-origin walk-forward backtest with Regime CQR
python src/backtest.py

# Generate SHAP explainability & diagnostic heatmaps
python src/error_diagnostics.py
```

---

## 📑 Master Documentation & Pitch Kit
Project documentation and pitch materials are available in `docs/`:
1. **[Delhi_DISCOM_PL_and_Pitch_Master_Guide.pdf](docs/Delhi_DISCOM_PL_and_Pitch_Master_Guide.pdf)**: Complete P&L financial analysis, 10-slide ready-to-present PPT deck, and rapid-fire judge defense cheat sheet.
2. **[Delhi_DISCOM_Project_Master_Technical_Report.pdf](docs/Delhi_DISCOM_Project_Master_Technical_Report.pdf)**: 5-page master technical dossier covering feature engineering, quantile LightGBM math, regime-conditioned CQR, and 52-window walk-forward validation.
