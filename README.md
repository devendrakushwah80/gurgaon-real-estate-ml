# Gurgaon Real Estate ML

Production-grade machine learning repository for Gurgaon real-estate price prediction, property recommendations, and market analytics.

The original notebook capstone has been refactored into a maintainable ML system with preserved datasets, archived experiments, reusable Python modules, trained model artifacts, FastAPI endpoints, a Streamlit app, tests, Docker, and CI/CD.

## Architecture

```text
data/                  raw, interim, processed, and external datasets
notebooks/             preserved experiments organized by workflow stage
src/                   reusable production Python package
app/                   FastAPI, Streamlit, and app service layers
models/                trained model and metadata artifacts
reports/               profiling, metrics, feature importance, and figures
deployment/            Docker, AWS, and CI/CD deployment assets
tests/                 pytest test suite
configs/               model and environment configuration
```

## Main Workflows

### Train

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements\dev.txt
venv\Scripts\python.exe -m src.models.train
```

Artifacts are written to:

- `models/price_model.joblib`
- `models/model_metadata.json`
- `reports/metrics/model_metrics.json`
- `reports/metrics/feature_importance.csv`

### API

```bash
venv\Scripts\uvicorn.exe app.api:api --reload
```

Endpoints:

- `GET /health`
- `POST /predict`
- `POST /batch_predict`
- `POST /recommend`
- `POST /similar_properties`

### Streamlit

```bash
venv\Scripts\streamlit.exe run app/streamlit_app.py
```

The frontend is organized as a modular enterprise Streamlit app:

- `app/pages`: dashboard, prediction, recommendations, analytics, batch prediction, model insights, and API health pages.
- `app/components`: reusable cards, charts, tables, sidebar, and page headers.
- `app/services`: API client, prediction service, recommendation service, and analytics data access.
- `app/assets`: shared CSS and logo.
- `.streamlit/config.toml`: dark professional theme configuration.

Start the FastAPI backend first for prediction, batch prediction, recommendation, and health workflows:

```bash
venv\Scripts\uvicorn.exe app.api:api --host 127.0.0.1 --port 8000
venv\Scripts\streamlit.exe run app/streamlit_app.py
```

### Tests and Lint

```bash
venv\Scripts\python.exe -m pytest
venv\Scripts\python.exe -m ruff check .
```

## Current Model

The production model is a sklearn `TransformedTargetRegressor` wrapping a preprocessing pipeline and `RandomForestRegressor`. The target is trained on `log1p(price)` and predictions are returned on the original crore scale.

Current validation metrics:

- R2: `0.8211`
- MAE: `0.5304 Cr`
- RMSE: `1.1727 Cr`

## Documentation

- `PROJECT_ANALYSIS.md`
- `DATA_FLOW.md`
- `NOTEBOOK_DEPENDENCY_GRAPH.md`
- `SYSTEM_DESIGN.md`
- `DATA_DICTIONARY.md`
- `MODEL_REPORT.md`
- `DEPLOYMENT_GUIDE.md`
- `FINAL_REFACTOR_SUMMARY.md`
