# EstateIQ — Gurgaon Real Estate Intelligence

Production-grade machine learning repository for Gurgaon real-estate price prediction, property recommendations, and market analytics.

The original notebook capstone has been incrementally upgraded into a maintainable ML system with preserved datasets, archived experiments, reusable Python modules, trained model artifacts, FastAPI endpoints, a Next.js user-facing frontend, an internal Streamlit dashboard, SQLite application state, authentication, RBAC, source-backed property intelligence, explainable Trust and Investment Scores, tests, Docker, and CI/CD.

## Architecture

```text
data/                  raw, interim, processed, and external datasets
notebooks/             preserved experiments organized by workflow stage
src/                   reusable production Python package
app/                   FastAPI, internal Streamlit dashboard, and services
frontend/              primary Next.js user-facing UI/UX
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

Legacy endpoints (preserved):

- `GET /health`
- `POST /predict`
- `POST /batch_predict`
- `POST /recommend`
- `POST /similar_properties`

EstateIQ endpoints:

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET/PUT /api/auth/preferences`
- `GET /api/properties`, `GET /api/properties/{id}`, `POST /api/properties/compare`
- `POST /api/recommendations`
- `GET /api/intelligence/{id}`, `/api/intelligence/trust/{id}`, `/api/intelligence/investment/{id}`, `/api/intelligence/predictions/fair-value/{id}`
- `POST/DELETE /api/properties/{id}/favorite`, `GET /api/properties/user/favorites`
- Agent listing CRUD under `/api/properties` (permission protected)
- `GET /api/admin/overview` and moderation under `/api/admin` (admin permission protected)

Property responses include the existing model-backed fair-value estimate where available, a classified difference from listing price, explainable Trust Score breakdown, independent Investment Score breakdown, recommendation reason, and original source URL. The current raw exports contain no image URL fields; the UI reports that limitation instead of fabricating images.

For predictable API latency on the current 15k+ source rows, discovery applies filters first and evaluates a deterministic, source-distributed candidate cap before running model-backed intelligence scoring. A production deployment should move this candidate retrieval to indexed database/vector search and a background score refresh queue.

### Legacy Streamlit internal dashboard

Do not use this command for the main EstateIQ UI. It starts the old internal dashboard on port `8501`. The primary user-facing UI is the Next.js app at `http://localhost:3000`.

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

### Benchmark

```bash
venv\Scripts\python.exe -m src.models.benchmark
```

This evaluates Random Forest, Extra Trees, and Gradient Boosting on the same fixed split and writes `reports/metrics/model_benchmark.json`. It does not replace the production artifact automatically.

### Application state and security

The local SQLite database is created at `data/estateiq.db` and contains users, roles, permissions, preferences, favourites, agent listings, score snapshots, verification requests, recommendation events, and audit logs. Copy `.env.example` to `.env` and set a strong `JWT_SECRET` before non-local use. Passwords use salted PBKDF2 hashing; JWTs are signed access tokens and are never logged.

Bootstrap the first administrator interactively (the password is not passed on the command line):

```bash
venv\Scripts\python.exe -m app.bootstrap_admin admin@example.com
```

## Next.js frontend

The normal user-facing EstateIQ application is now the independent Next.js frontend in `frontend/`. Streamlit remains available only as an internal/debug dashboard.

### Frontend setup

```powershell
cd frontend
Copy-Item .env.example .env.local
npm.cmd install
npm.cmd run dev
```

The frontend reads `NEXT_PUBLIC_API_URL` from `frontend/.env.local` and defaults to `http://127.0.0.1:8000`.

Default URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`

Frontend verification commands:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

Main frontend routes include `/`, `/login`, `/signup`, `/properties`, `/property/[id]`, `/dashboard`, `/saved`, `/compare`, `/profile`, `/agent`, `/agent/listings/new`, and `/admin`. Backend permissions remain authoritative for all protected operations.

## Current Model

The production model is a sklearn `TransformedTargetRegressor` wrapping a preprocessing pipeline and `RandomForestRegressor`. The target is trained on `log1p(price)` and predictions are returned on the original crore scale.

Current validation metrics:

- R2: `0.8211`
- MAE: `0.5304 Cr`
- RMSE: `1.1727 Cr`

## Cloud Deployment

### 1. Backend API Deployment (Render)
1. Log in to [Render](https://render.com) and create a **New Web Service**.
2. Connect your GitHub repository (`devendrakushwah80/gurgaon-real-estate-ml`).
3. Render automatically reads `render.yaml` or set the following settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.api:api --host 0.0.0.0 --port $PORT`
4. Deploy the service and copy your live Render service URL (e.g., `https://gurgaon-real-estate-backend.onrender.com`).

### 2. Next.js frontend deployment

Deploy `frontend/` to a Next.js-compatible host and set:

```text
NEXT_PUBLIC_API_URL=https://your-backend.example.com
```

Add the frontend origin to the backend `ALLOWED_ORIGINS` environment variable. Streamlit can remain deployed separately for internal diagnostics if required.

## Documentation

- `PROJECT_ANALYSIS.md`
- `DATA_FLOW.md`
- `NOTEBOOK_DEPENDENCY_GRAPH.md`
- `SYSTEM_DESIGN.md`
- `DATA_DICTIONARY.md`
- `MODEL_REPORT.md`
- `DEPLOYMENT_GUIDE.md`
- `FINAL_REFACTOR_SUMMARY.md`

## Cities, freshness, and source policy

EstateIQ supports canonical cities `gurgaon` (including the Gurgaon/Gurugram alias) and `indore`. The city selector routes discovery to a city-specific API query. Historical CSV exports are not overwritten: newly verified source records are stored separately in `data/estateiq.db` under `current_listings`.

Responsible 99acres verification uses public URLs only:

```powershell
venv\Scripts\python.exe -m src.ingestion.run --city gurgaon --pages 20
venv\Scripts\python.exe -m src.ingestion.run --city indore --pages 20
venv\Scripts\python.exe -m src.ingestion.run --all --pages 20
```

The adapter uses a descriptive user agent, a delay, a timeout, limited retries, and records HTTP blocks or unreachable responses. It does not bypass robots rules, CAPTCHA, rate limits, or anti-bot controls. It attaches an image only when the exact listing response contains a verifiable JSON-LD, OpenGraph, or embedded image URL; generic or random images are never assigned. Records classified `REMOVED`, `STALE`, or `UNREACHABLE` are excluded from normal discovery.

Ingestion reports separate `pages_fetched`, `listing_candidates`, `listings_parsed`, `unique_listings`, `detail_pages_fetched`, `images_extracted`, and `stored_listings`. Search-page URLs are never stored as property URLs; every stored source URL must be an individual detail URL. Pagination uses the public `page=` parameter, stops on repeated response hashes or consecutive pages with no new source IDs, and saves only the first debug response under `debug/99acres/`.

For the legacy labelled-data workflow, city-aware model training remains gated on labelled data for each city:

```powershell
venv\Scripts\python.exe -m src.models.city_aware --data-path path\to\city_labelled_data.csv
```

The existing production model remains unchanged as the historical Gurgaon baseline (`R2 0.8211`, `MAE 0.5304 Cr`, `RMSE 1.1727 Cr`).

### Parse 99acres provider

Parse `search_properties` is the primary provider when `PARSE_99ACRES_API_KEY` is configured. Its documented contract uses `page`, `location`, `property_type`, and `transaction_type`, and returns `data.properties`, `total_count`, and `current_page`. EstateIQ maps the documented fields (`property_id`, `property_name`, `price`, `area`, `bedrooms`, `locality`, `city`, `details_url`, `images`, `posted_date`, `seller_name`, `is_verified`, amenities, and coordinates) into the normalized catalog while retaining a compact raw payload. Parse is an independent wrapper, not an official 99acres API.

```powershell
Copy-Item .env.example .env
# Set PARSE_99ACRES_API_KEY in .env; never commit it.
venv\Scripts\python.exe -m src.ingestion.run --city indore --pages 3 --provider parse
venv\Scripts\python.exe -m src.ingestion.run --city gurgaon --pages 3 --provider parse
```

Provider choices are `parse`, `apify`, `direct`, and `auto`. `auto` selects Parse when its key exists, then Apify when its token exists, and otherwise uses the direct adapter. Use `direct` only for fallback/debugging. Apify runs the configured `rigelbytes~99acres-scraper` actor through the documented synchronous dataset endpoint; it passes city-specific exact search URLs and normalizes the actor's property records, detail URLs, dates, seller fields, coordinates, and gallery images. The first response is saved under ignored `debug/99acres/` for audit, and each report includes API requests, candidate/parsed/unique/stored counts, images, duplicates, invalid records, API errors, and sample IDs/URLs.

Do not train city-aware models until both cities pass the 3-page smoke test and their samples show distinct source IDs and exact original URLs. Only then prepare labelled training data and compare Gurgaon, Indore, and overall metrics against the unchanged baseline; no improvement is claimed without a same-split, leakage-safe evaluation.

After the verified smoke runs, the fresh asking-price benchmark can be built with:

```powershell
venv\Scripts\python.exe -m src.models.fresh_city_benchmark
```

This writes `data/processed/verified_current_city_listings.csv`, `models/fresh_city_models.joblib`, and `reports/metrics/fresh_city_model_benchmark.json`. It trains separate city models, reports Gurgaon, Indore, and overall holdout metrics, and excludes target-derived fields such as `price_per_sqft`. These are current asking-price metrics on a different population from the historical baseline; the report therefore sets `improvement_claimed` to `false` and does not replace the production artifact.

