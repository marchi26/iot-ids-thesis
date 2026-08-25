# IoT IDS Thesis Project

Bachelor's thesis project for Computer Engineering:

**Sicurezza nei sistemi Internet of Things: architetture, vulnerabilità e strategie di mitigazione**

This repository contains the experimental work for an IoT intrusion detection thesis, based on the supervisor reference repository `KuznetsovKarazin/iot-audit`.

## Objective

The project provides a Python pipeline for TON_IoT / UNSW network intrusion detection experiments:

- binary classification: normal vs attack;
- multiclass classification: attack type classification;
- baseline models: Random Forest, LightGBM, XGBoost, Logistic Regression;
- extended experiments: SMOTE balancing, hyperparameter tuning, MLPClassifier and Isolation Forest;
- additional analysis: per-class summaries, latency summaries, model compression, and feature-importance interpretability;
- embedded deployment demonstrator: exported quantized Logistic Regression model for ESP32/Wokwi;
- metrics, plots, and Italian thesis notes.

Metrics and plots are produced by the experiment scripts. The raw dataset is not included in the repository.

## Repository Structure

```text
config/                 Configuration file
data/raw/               Local raw datasets, excluded from Git
data/processed/         Optional processed datasets, excluded from Git
src/data/               Loading and preprocessing
src/models/             Training, evaluation, and extended experiments
src/experiments/        Root-callable experiment runners
src/simulation/         MQTT IoT simulation components
src/visualization/      Plot utilities
src/experiments/        Experiment runners and analysis/export scripts
results/metrics/        Generated CSV metrics and tables
results/plots/          Generated PNG plots
results/models/         Optional trained models, excluded from Git
results/logs/           Runtime logs, excluded from Git
thesis/                 Italian thesis notes and draft sections
thesis/final_thesis.docx Final Word document generated from the consolidated thesis draft
scripts/                Setup and execution helpers
wokwi/                  ESP32 Wokwi deployment demonstrator
```

## Dataset

Use the TON_IoT / UNSW network dataset. The expected file is:

```text
data/raw/train_test_network.csv
```

The CSV must contain at least:

- `label` for binary classification;
- `type` for multiclass classification.

Raw datasets are excluded from Git and must not be committed.

Optional Kaggle helper scripts are available:

```powershell
.\scripts\setup_kaggle_auth.ps1
.\scripts\download_dataset.ps1
```

Kaggle credentials must stay local. The `.kaggle/` directory and `kaggle.json` are ignored by Git.

## Environment Setup

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run Experiments

Binary baseline:

```bash
python src/experiments/run_binary.py
```

Multiclass baseline:

```bash
python src/experiments/run_multiclass.py
```

Extended experiments:

```bash
python src/experiments/run_extended.py
```

Result summaries:

```bash
python src/experiments/generate_result_summary.py
```

Interpretability analysis:

```bash
python src/experiments/run_interpretability.py
```

The interpretability runner uses SHAP, included in `requirements.txt`, and records the method in the generated CSV. A native tree-feature-importance fallback is retained only to provide a clear degraded mode if SHAP is unavailable; the committed thesis results were generated with SHAP.

Deployment-oriented model size and latency analysis:

```bash
python src/experiments/run_deployment_analysis.py
```

Embedded ESP32/Wokwi model export:

```bash
python src/experiments/export_embedded_model.py
```

This command trains a compact binary Logistic Regression model on selected numeric TON_IoT features, exports quantized coefficients to `wokwi/ids_esp32/include/embedded_model.h`, and compares the original floating-point Python model with an `int16` quantized emulation over the complete test set. Both rows are written to `results/metrics/embedded_logistic_regression_metrics.csv`.

Baselines, extended experiments, and result summaries:

```bash
python src/experiments/run_all.py
```

`run_all.py` executes `run_binary.py`, `run_multiclass.py`, `run_extended.py`, and `generate_result_summary.py`. It does not execute SHAP interpretability, deployment/compression analysis, embedded model export, or the MQTT/Wokwi simulation; use the dedicated commands above for those analyses.

If the dataset is missing, the scripts stop with a clear message.

## IoT Simulation

Run the lightweight MQTT simulation:

```bash
docker compose up --build
```

The simulation includes:

- Eclipse Mosquitto MQTT broker;
- normal IoT device publisher;
- anomalous traffic publisher;
- traffic collector that writes `results/metrics/simulated_iot_traffic.csv`.

The simulation is a supporting component for discussion and does not replace the TON_IoT dataset.

## ESP32 / Wokwi Demonstrator

The directory `wokwi/ids_esp32/` contains a PlatformIO/Wokwi project for an ESP32 inference demo. It uses the generated `embedded_model.h` header and runs local binary IDS inference on sample feature vectors exported from the TON_IoT dataset.

Browser Wokwi project:

```text
https://wokwi.com/projects/472799587810026497
```

Optional local commands:

```powershell
cd wokwi\ids_esp32
pio run
wokwi-cli .
```

`pio` and `wokwi-cli` are optional external tools. Wokwi CLI also requires a local `WOKWI_CLI_TOKEN`; do not commit tokens or credentials.

For the browser-only workflow:

```powershell
.\scripts\open_wokwi_browser.ps1
```

Then follow `wokwi/browser_esp32/README.md` and paste/import `sketch.ino`, `embedded_model.h`, and `diagram.json` into a Wokwi ESP32 web project.

## Outputs

After running the experiments, the main outputs include:

- `results/metrics/binary_baseline_metrics.csv`
- `results/metrics/multiclass_baseline_metrics.csv`
- `results/metrics/binary_extended_metrics.csv`
- `results/metrics/multiclass_extended_metrics.csv`
- `results/metrics/smote_comparison.csv`
- `results/metrics/hyperparameter_tuning_results.csv`
- `results/metrics/per_class_summary.csv`
- `results/metrics/latency_summary.csv`
- `results/metrics/deployment_analysis.csv`
- `results/metrics/embedded_logistic_regression_metrics.csv`
- `results/metrics/interpretability_feature_importance.csv`
- `results/plots/*.png`
- `results/logs/*.log`

## Reproducibility

- Fixed random seed: `42`.
- Configuration is centralized in `config/config.yaml`.
- Encoders and scalers are fitted only on the training split.
- SMOTE is applied only to the training split.
- Datasets and trained models are excluded from Git.
- PlatformIO and Wokwi build outputs are excluded from Git.

## Notes and Limitations

The pipeline depends on the availability and exact schema of `train_test_network.csv`. Extended experiments can be computationally expensive on large datasets. Static benchmark datasets do not fully represent real deployment drift, encrypted traffic, device heterogeneity, or adversarial adaptation.

The ESP32/Wokwi demo uses a compact exported model and does not reproduce the full LightGBM baseline on embedded hardware. It is intended to support the deployment discussion, not to replace the main experimental evaluation.
