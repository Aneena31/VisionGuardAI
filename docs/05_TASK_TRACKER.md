# VisionGuard AI - Task Tracker

## Current Status

Updated 2026-06-04: Backend source files for Phases 1-5 are implemented. Syntax/import smoke checks pass under the project `venv`. Local seed and API verification pass using the available 5-row workbook copied to `data/Sample_Data_for_ML.xlsx`; full 10,000-row validation still requires the full workbook. React UI now reads from the FastAPI backend through `VITE_API_BASE_URL`; build and TypeScript checks pass.

## Build Phases

```
Phase 1 - Foundation (Database + Pipeline)
Phase 2 - Core API (Must-have endpoints)
Phase 3 - AI Summary Layer (ChatOpenAI integration)
Phase 4 - Scoring Job System (New Claim)
Phase 5 - Supporting API (Actions, export, search)
Phase 6 - Integration + Testing
```

---

## Phase 1 - Foundation

### 1.1 Project Setup
- [x] Create `visionguard/` root folder
- [x] Create `requirements.txt` with all dependencies
- [x] Create `.env.example`
- [x] Create `README.md` with setup instructions
- [x] Initialize git repo

### 1.2 Database Setup
- [x] Create `db/database.py` - engine, session factory, `get_db` dependency
- [x] Create `db/models.py` - Claim, ProviderGold, ScoringJob, Notification, PipelineRun
- [x] Call `Base.metadata.create_all(engine)` on startup

### 1.3 Pipeline - Ingest
- [x] Create `pipeline/ingest.py`
- [x] `load_and_clean(file_path)`
- [x] `clean_single(claim_dict)`

### 1.4 Pipeline - Rules
- [x] Create `pipeline/rules.py`
- [x] `apply_rules(df)` implements R001-R011
- [x] `generate_rule_narratives(df)`
- [x] `apply_rule_scoring(df)`

### 1.5 Pipeline - Statistics
- [x] Create `pipeline/stats.py`
- [x] `apply_statistical_outliers(df)`
- [x] `score_single_claim(claim_dict, population_stats)`
- [x] `get_population_stats(db)`

### 1.6 Pipeline - ML
- [x] Create `pipeline/ml.py`
- [x] `apply_unsupervised_ml(df)`
- [x] `save_artifacts(scaler, iso, pca, ml_features, path)`
- [x] `load_artifacts(path)`
- [x] `score_single(claim_dict, artifacts)`

### 1.7 Pipeline - Scoring
- [x] Create `pipeline/scoring.py`
- [x] `apply_final_scoring(df)`
- [x] `apply_final_scoring_single(scores_dict)`

### 1.8 Pipeline - Similarity
- [x] Create `pipeline/similarity.py`
- [x] `compute_similarity(df)` returns empty lists for POC with TODO for cosine similarity

### 1.9 Pipeline - Aggregation
- [x] Create `pipeline/aggregation.py`
- [x] `build_provider_gold(df)`
- [x] Deterministic provider names, specialties, cities, and states

### 1.10 Pipeline - Orchestrator
- [x] Create `pipeline/pipeline.py`
- [x] `run_batch(file_path)`
- [x] `run_single(claim_dict, artifacts, population_stats)`

### 1.11 Database Seed
- [x] Create `db/seed.py`
- [x] Calls `pipeline.run_batch()`
- [x] Converts DataFrames to ORM model instances
- [x] Bulk inserts into `claims` and `provider_gold`
- [x] Creates initial `PipelineRun` record
- [x] Run `python db/seed.py` end-to-end using local 5-row workbook

---

## Phase 2 - Core API

### 2.1 FastAPI App Setup
- [x] Create `api/main.py`
- [x] FastAPI app init
- [x] CORS middleware from `CORS_ORIGINS`
- [x] Include all routers
- [x] Startup event creates DB tables and checks artifacts
- [x] Health check: `GET /health`

### 2.2 Pydantic Schemas
- [x] Create `api/schemas/common.py` - ResponseEnvelope, ErrorSchema, PaginationSchema, `make_response`
- [x] Create `api/schemas/claim.py`
- [x] Create `api/schemas/provider.py`
- [x] Create `api/schemas/dashboard.py`
- [x] Create `api/schemas/scoring.py`

### 2.3 Dashboard Endpoint
- [x] Create `api/routers/dashboard.py`
- [x] `GET /visionguard/dashboard/overview`
- [x] `POST /visionguard/dashboard/export`

### 2.4 Claims Endpoints
- [x] Create `api/routers/claims.py`
- [x] `GET /visionguard/claims`
- [x] Search/filter/sort/paginate
- [x] `GET /visionguard/claims/:claimId`
- [x] `POST /visionguard/claims/:claimId/flag-siu`
- [x] `GET /visionguard/claims/:claimId/report`

### 2.5 Provider Endpoints
- [x] Create `api/routers/providers.py`
- [x] `GET /visionguard/providers`
- [x] `GET /visionguard/providers/:providerId`
- [x] Dynamic `procedurePeerComparison`

### 2.6 System Status Endpoint
- [x] Create `api/routers/system.py`
- [x] `GET /visionguard/system/status`

---

## Phase 3 - AI Summary Layer

### 3.1 ChatOpenAI Integration
- [x] Create `pipeline/ai_summary.py`
- [x] `generate_for_claim(claim_dict)`
- [x] `generate_batch(df, score_threshold=40)`
- [x] Structured prompt and JSON parsing
- [x] Fallback summary on any API failure
- [x] Batch rate limit uses documented `time.sleep(0.3)`

### 3.2 Provider-Level AI Summary
- [x] ChatOpenAI provider-level summaries for providers with `provider_risk_score > 60`
- [x] Deterministic provider-level summary fields for POC API contract

### 3.3 Integrate into Seed
- [x] Seed stores claim `ai_summary` JSON string

---

## Phase 4 - Scoring Job System

### 4.1 Scoring Router
- [x] Create `api/routers/scoring.py`
- [x] `POST /visionguard/scoring/jobs`
- [x] `GET /visionguard/scoring/jobs/:jobId`
- [x] `GET /visionguard/scoring/jobs/:jobId/result`
- [x] `POST /visionguard/scoring/jobs/:jobId/assign-siu`

### 4.2 Pipeline Background Task
- [x] Create `api/services/scoring_service.py`
- [x] Updates validating/processing/completed/failed job state
- [x] Uses cached artifacts and population stats from app startup
- [x] Stores full ClaimAnalysis JSON in `scoring_jobs.result_json`
- [x] Creates notification for Critical results

### 4.3 File Upload Support
- [x] Accept `.xlsx`, `.csv`, `.json`
- [x] Parse first row as claim data
- [x] Feed to same scoring path as manual entry

---

## Phase 5 - Supporting API

- [x] Claim SIU flag action
- [x] Claim report static response
- [x] Dashboard export static response
- [x] `GET /visionguard/search?query=`
- [x] `GET /visionguard/notifications`
- [x] Optional notification read endpoint

---

## Phase 6 - Integration + Testing

### 6.1 Integration
- [x] Run `python db/seed.py` end-to-end using local 5-row workbook
- [x] Start `uvicorn api.main:app --reload`
- [x] Verify seeded must-have endpoints return real data
- [x] Browser-verify all five React screens load real data

### 6.2 Smoke Checks Completed
- [x] `python -m compileall pipeline db api`
- [x] FastAPI import and schema initialization
- [x] `GET /health` returns envelope
- [x] `GET /visionguard/system/status` returns envelope
- [x] `GET /visionguard/dashboard/overview` returns envelope on empty DB
- [x] Missing workbook fails clearly in `db/seed.py`
- [x] Scoring endpoint returns envelope-shaped 503 before artifacts exist
- [x] Seeded dashboard, claims, providers, claim detail, provider detail, scoring job status/result
- [x] React API client wired to `VITE_API_BASE_URL`
- [x] React production build passes
- [x] React TypeScript check passes

### 6.3 Edge Cases Covered In Code
- [x] `AllowedAmount = 0` ratio protection
- [x] Provider with one claim / zero std z-score protection
- [x] OpenAI unavailable fallback summary
- [x] Job failure status and error message path

---

## Dependency Map

```
Phase 1 -> Phase 2 -> Phase 4/5 -> Phase 6
Phase 3 claim summaries are integrated with Phase 1 seed and Phase 4 scoring.
```
