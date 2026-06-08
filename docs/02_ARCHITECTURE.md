# VisionGuard AI — Architecture

## System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│                                                                  │
│   React UI (visionguard-ui)                                      │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────┐  │
│   │  Executive   │ │   Claims     │ │  Provider    │ │ New   │  │
│   │  Dashboard   │ │  Explorer    │ │ Intelligence │ │ Claim │  │
│   └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └───┬───┘  │
└──────────┼────────────────┼────────────────┼─────────────┼──────┘
           │                │                │             │
           └────────────────┴────────────────┴─────────────┘
                                    │
                              HTTP / REST
                                    │
┌──────────────────────────────────────────────────────────────────┐
│                        API LAYER (FastAPI)                       │
│                                                                  │
│  /visionguard/dashboard    /visionguard/claims    /visionguard/providers   /visionguard/scoring  │
│  /visionguard/search       /visionguard/notifications              /visionguard/system   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Service Layer                          │   │
│  │  DashboardService  ClaimService  ProviderService          │   │
│  │  ScoringService    SearchService                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
           │                                        │
    DB reads/writes                          pipeline calls
           │                                        │
┌──────────┴──────────┐              ┌──────────────┴──────────────┐
│   DATABASE LAYER    │              │      PIPELINE LAYER         │
│                     │              │                             │
│  SQLite (dev)       │              │  ingest.py                  │
│  PostgreSQL (prod)  │              │  rules.py      (R001–R011)  │
│                     │              │  stats.py      (Z-scores)   │
│  Tables:            │              │  ml.py         (IF + PCA)   │
│  - claims           │              │  scoring.py    (composite)  │
│  - providers        │              │  narrative.py  (text)       │
│  - scoring_jobs     │              │  similarity.py (cosine)     │
│  - provider_gold    │              │  ai_summary.py (ChatOpenAI) │
│  - notifications    │              │  pipeline.py   (orchestrate)│
└─────────────────────┘              └─────────────────────────────┘
                                                    │
                                          ┌─────────┴────────┐
                                          │  OpenAI API      │
                                          │  gpt-4o          │
                                          │  (AI Summary)    │
                                          └──────────────────┘
```

---

## Pipeline Architecture (Deep Dive)

The pipeline is the core of VisionGuard. It runs in two modes:

### Mode 1 — Batch Seed (Historical)
Run once at startup. Processes all 10k rows from the Excel file and persists results to the database. After seeding, the API only reads from the DB for historical queries — the pipeline doesn't re-run on every API call.

```
seed.py
  └── pipeline.run_batch(df_raw)
        ├── ingest.load_and_clean()
        ├── rules.apply_rules()
        ├── rules.generate_narratives()
        ├── scoring_rules.apply_rule_scoring()
        ├── stats.apply_statistical_outliers()
        ├── ml.apply_unsupervised_ml()          ← trains models, saves artifacts
        ├── scoring.apply_final_scoring()
        ├── similarity.compute_similarity()
        ├── ai_summary.generate_case_summary()  ← batched ChatOpenAI calls
        ├── aggregation.build_provider_gold()
        └── db.persist_all()
```

**ML Model Artifacts** (saved after batch run for reuse in real-time scoring):
- `artifacts/scaler.pkl`
- `artifacts/isolation_forest.pkl`
- `artifacts/pca.pkl`
- `artifacts/ml_features.json` (feature list, for consistency)

### Mode 2 — Real-Time Scoring (New Claim)
Single-claim scoring triggered via API. Loads saved model artifacts instead of retraining.

```
POST /visionguard/scoring/jobs
  └── ScoringService.create_job(claim_input)
        ├── validate claim format
        ├── auto-generate ClaimId (UUID-based, e.g. "TEMP-CLAIM-{uuid4().hex[:8]}")
        ├── pipeline.run_single(claim_dict)
        │     ├── ingest.clean_single()
        │     ├── rules.apply_rules_single()
        │     ├── stats.score_single_claim()     ← uses population stats from DB
        │     ├── ml.score_single()              ← loads pkl artifacts
        │     ├── scoring.apply_final_scoring_single()
        │     ├── narrative.generate_all()
        │     └── ai_summary.generate_for_claim() ← ChatOpenAI call
        └── ScoringJob persisted with status + result
```

---

## AI Summary Layer (ChatOpenAI)

This is the explainability layer — the part missing from the original notebook.

**How it works:**

For each claim (or new scored claim), after the pipeline runs, a structured prompt is sent to `gpt-4o`:

```python
system_prompt = """You are a healthcare fraud analyst AI assistant for an insurance SIU team.
Given structured claim analysis data, generate a concise, professional fraud investigation summary.
Return JSON with keys: summary, riskReasoning, recommendation."""

user_prompt = f"""
Claim: {procedure_code} — {procedure_desc}
Provider: {provider_id}
Allowed Amount: ${allowed_amount}
Member Age: {member_age}

Rule Engine Results:
- Rule Score: {rule_score_total}/100
- Triggered Rules: {rule_narrative}

Statistical Analysis:
- Claim Z-Score (Allowed): {z_allowed:.2f}
- Provider Z-Score: {z_provider:.2f}
- Statistical Narrative: {ml_narrative}

ML Detection:
- Isolation Forest Score: {if_score_norm:.1f}/100
- PCA Reconstruction Error Score: {pca_score_norm:.1f}/100
- ML Narrative: {ml_anomaly_narrative}

Final Combined Score: {final_combined_score:.1f}/100
Risk Level: {final_risk_level}
Suspected Fraud Type: {final_fraud_type}

Generate a 3-part investigation summary (summary, riskReasoning, recommendation).
Be specific. Reference actual rule codes and scores. Keep each field under 100 words.
"""
```

**Batching for seed run:** To avoid 10k individual API calls, the seed run only calls ChatOpenAI for claims with `Final_Combined_Score > 40` (Medium, High, Critical risk). Low-risk claims get a template-generated summary without an LLM call.

**Cost control:** Estimated ~3,000 Medium+ claims × ~500 tokens = ~1.5M tokens. At gpt-4o-mini pricing this is < $1 for the full seed run.

---

## Database Architecture

### Dev: SQLite
- File: `visionguard.db`
- Zero setup, works out of the box

### Prod: PostgreSQL
- Connection via `DATABASE_URL` env var
- SQLAlchemy handles both dialects transparently

### Connection Management
```python
# db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # SQLite only
SessionLocal = sessionmaker(bind=engine)
```

---

## Async Job Pattern (New Claim Scoring)

New claim scoring runs asynchronously so the UI can show pipeline progress stages.

```
POST /visionguard/scoring/jobs          → creates ScoringJob record, status="queued", returns jobId
GET  /visionguard/scoring/jobs/:jobId   → polls status + progressPercent + activeStage
GET  /visionguard/scoring/jobs/:jobId/result  → returns full ClaimAnalysis once status="completed"
```

**Implementation options:**
1. **Simple (POC recommended):** Use Python `threading` or `asyncio.create_task`. FastAPI runs the pipeline in a background task. Status is updated in-process.
2. **Production:** Celery + Redis queue. Overkill for POC.

**Recommended for POC:** FastAPI `BackgroundTasks`:
```python
@router.post("/scoring/jobs")
async def create_scoring_job(claim: ClaimInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = create_job_record(db, claim)
    background_tasks.add_task(run_pipeline_and_update_job, job.id, claim, db)
    return {"data": {"jobId": job.id, "status": "queued"}}
```

---

## Environment Variables

```
# .env.example
DATABASE_URL=sqlite:///./visionguard.db
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ARTIFACTS_PATH=./artifacts
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

## CORS Configuration

The React UI runs on a different port than the API in development. FastAPI must allow cross-origin requests:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Pipeline Scoring Weights (Tunable)

These are defined in `scoring.py` and should be easily configurable:

| Component | Weight | Rationale |
|---|---|---|
| Rule Score | 35% | Deterministic, highest precision |
| Claim Stat Score | 20% | Individual claim anomaly |
| Provider Stat Score | 20% | Provider-level pattern |
| ML Anomaly Score | 25% | Non-linear pattern detection |

Provider Gold Score weights:

| Component | Weight |
|---|---|
| High-Risk Claim Ratio | 35% |
| Avg Final Score | 25% |
| Avg ML Score | 25% |
| Avg Provider Stat Score | 15% |

---

## Scalability Notes (For Future Reference)

- The 10k-row batch seed takes ~2–3 minutes locally (dominated by ChatOpenAI calls)
- For production scale (1M+ claims), move pipeline to Spark/Databricks (Fabric-ready, as noted in original notebook)
- Similarity engine (`compute_similarity`) uses O(n²) cosine similarity — works for 10k, needs ANN (FAISS/Qdrant) at 100k+
- Provider-level Z-scores should be pre-computed nightly, not per-request
