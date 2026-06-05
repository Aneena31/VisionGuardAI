# VisionGuard AI — Codex Kickstart Prompt

## Instructions for Codex

Paste the following prompt to start a Codex session. It contains everything needed to begin building the backend from scratch.

---

## KICKSTART PROMPT

```
You are building the backend for VisionGuard AI — a vision insurance claims fraud detection platform.

The frontend (React UI) already exists. Your job is to build:
1. A fraud detection pipeline (Python)
2. A FastAPI REST API
3. A SQLite database layer
4. A seed script that runs the pipeline on historical data

READ the docs/ folder carefully before writing any code. Every architectural decision is documented there. Do not deviate from documented schemas, naming conventions, or response envelopes without flagging it.

---

PROJECT STRUCTURE (create this exactly):

visionguard/
├── docs/                   ← Already exists — do not modify
├── data/
│   └── Sample_Data_for_ML.xlsx
├── artifacts/              ← ML model pkl files go here (created by seed)
├── pipeline/
│   ├── __init__.py
│   ├── config.py           ← All tunable thresholds
│   ├── ingest.py           ← Load + clean Excel data
│   ├── rules.py            ← Rule engine R001–R011
│   ├── stats.py            ← Z-score statistical engine
│   ├── ml.py               ← Isolation Forest + PCA
│   ├── scoring.py          ← Final weighted composite score
│   ├── narrative.py        ← Human-readable rule + ML explanations
│   ├── similarity.py       ← Cosine similarity similar claims
│   ├── aggregation.py      ← Build provider_gold table
│   ├── ai_summary.py       ← ChatOpenAI explainability layer
│   └── pipeline.py         ← Orchestrator: run_batch() + run_single()
├── db/
│   ├── __init__.py
│   ├── database.py         ← SQLAlchemy engine + session
│   ├── models.py           ← All ORM models
│   └── seed.py             ← Run pipeline, persist to DB
├── api/
│   ├── __init__.py
│   ├── main.py             ← FastAPI app, CORS, routers, startup
│   ├── routers/
│   │   ├── dashboard.py
│   │   ├── claims.py
│   │   ├── providers.py
│   │   ├── scoring.py
│   │   ├── search.py
│   │   ├── notifications.py
│   │   └── system.py
│   ├── schemas/
│   │   ├── claim.py
│   │   ├── provider.py
│   │   ├── dashboard.py
│   │   ├── scoring.py
│   │   └── common.py
│   └── services/
│       ├── claim_service.py
│       ├── provider_service.py
│       ├── dashboard_service.py
│       └── scoring_service.py
├── requirements.txt
├── .env.example
└── README.md

---

STEP 1 — START HERE: Build in this exact order

1. requirements.txt
2. .env.example
3. pipeline/config.py       ← All thresholds in one place
4. pipeline/ingest.py
5. pipeline/rules.py
6. pipeline/stats.py
7. pipeline/ml.py
8. pipeline/scoring.py
9. pipeline/narrative.py    (can be merged into rules.py)
10. pipeline/similarity.py
11. pipeline/aggregation.py
12. pipeline/ai_summary.py
13. pipeline/pipeline.py    ← Orchestrates all of the above
14. db/database.py
15. db/models.py
16. db/seed.py
17. api/schemas/*.py        ← All Pydantic models
18. api/main.py
19. api/routers/dashboard.py
20. api/routers/claims.py
21. api/routers/providers.py
22. api/routers/scoring.py
23. api/routers/system.py
24. api/routers/search.py
25. api/routers/notifications.py
26. api/services/*.py

---

KEY RULES — FOLLOW THESE WITHOUT EXCEPTION:

1. ALL API responses must use this envelope:
   { "data": {}, "meta": { "requestId": "...", "generatedAt": "..." }, "error": null }
   Define a helper function `make_response(data, request_id)` in api/schemas/common.py.

2. Use a consistent ID generation convention (see docs/04_DATA_MODEL.md).
   Claims: "CLM-{raw_claim_id}"
   Providers: "PRV-{last 7 digits of raw ProviderId}"
   New scored claims: "TEMP-{YYYYMMDD}-{uuid4[:8]}"

3. All pipeline steps operate on a pandas DataFrame and return a DataFrame.
   The only exception is run_single() which works on dicts.

4. ML artifacts (scaler.pkl, isolation_forest.pkl, pca.pkl, ml_features.json) are saved
   to the ARTIFACTS_PATH directory after seed. The API loads them on startup and caches
   them in memory. Do NOT retrain the model on each new claim scoring request.

5. For the AI summary (ChatOpenAI):
   - Only call the API for claims with Final_Combined_Score >= 40 during batch
   - Use gpt-4o-mini model
   - System prompt and user prompt are defined in docs/06_PIPELINE_REFERENCE.md
   - Always have a fallback template if the API fails
   - Store the result as a JSON string in the `ai_summary` DB column

6. New Claim Scoring is ASYNC:
   - POST creates a job and returns jobId immediately
   - Use FastAPI BackgroundTasks to run the pipeline
   - GET /jobs/:id polls status + progress
   - GET /jobs/:id/result returns the full analysis

7. For dev, use SQLite. The DATABASE_URL env var controls the connection string.
   SQLAlchemy handles both SQLite and PostgreSQL — don't use SQLite-specific syntax.

8. Populate `provider_name`, `specialty`, `city`, `state` in provider_gold with
   synthetic but realistic values. Generate them deterministically from the ProviderId
   (e.g., hash to pick from a lookup list of names). The UI displays these prominently.

9. For `procedurePeerComparison` in provider detail:
   Query DB for: for each procedure code the provider billed, count their volume vs
   AVG volume across all providers who billed that code.

10. CORS: allow origins from CORS_ORIGINS env var (comma-separated). Default:
    "http://localhost:3000,http://localhost:5173"

---

IMPORTANT DATA NOTES:

The Excel file has 10,000 rows and 55 columns. Key columns used:
- ProcedureCode: V-codes (e.g. V2421, V2763) — NOT CPT codes
- AllowedAmount: maps to AmtAllowed
- UnitsUsed: maps to Units
- MemberAge: maps to PatientAge
- AmtCharged: billed amount (used for ratio)
- ProviderId: raw numeric, needs formatting
- ServiceCategoryName: contains "frame", "lens", "material" strings
- BenefitCategoryName: contains "material" string
- BenefitType: Exam | Lens | Frame | Contact | Other
- ServiceMonth: datetime (first day of service month)

The ProcedureCode column contains synthetic V-codes like V2421, V1826, V2838 etc.
Rules R001–R005 match specific V-code ranges. For the test dataset, R001–R005 will have
relatively low hit rates. R006–R009 will have more hits since they use numeric thresholds
on AmtAllowed and BilledAmountToAllowedRatio.

---

START NOW.

Build requirements.txt first, then pipeline/config.py, then pipeline/ingest.py.
After each file, confirm it is complete before moving to the next.
Ask for clarification only if something is genuinely ambiguous — prefer making a reasonable decision and noting it.
```

---

## Second Session Prompt (If Continuing)

If continuing in a new Codex session after Phase 1 is complete:

```
We are continuing to build VisionGuard AI. The pipeline and DB layer are complete.
Phase 1 is done. Now build Phase 2: the FastAPI API layer.

Reference docs/03_API_CONTRACTS.md for all endpoint schemas.
Reference docs/07_UI_GUIDE.md to understand what each screen expects.

The database is seeded with 10,000 processed claims and provider_gold records.
All pipeline scores are already computed and stored in the DB.

Start with:
1. api/schemas/common.py  — ResponseEnvelope, PaginationSchema, make_response helper
2. api/schemas/claim.py   — ClaimSummary, ClaimDetail, ClaimAnalysis
3. api/schemas/provider.py
4. api/main.py            — FastAPI app + all middleware + router includes
5. api/routers/dashboard.py
6. api/routers/claims.py
```

---

## Third Session Prompt (Scoring Jobs)

```
We are continuing to build VisionGuard AI. Phases 1 and 2 are complete.
The batch pipeline runs, DB is seeded, and core read API endpoints work.

Now build Phase 4: New Claim Scoring (async job system).

Key constraints:
- Use FastAPI BackgroundTasks (NOT Celery)
- Load ML artifacts from ARTIFACTS_PATH on API startup, cache in app.state
- Load population stats from DB on startup, cache in app.state
- Scoring job must update progress_percent + active_stage at each pipeline step
- Final result stored as JSON blob in scoring_jobs.result_json
- Claim ID for new claims: "TEMP-{YYYYMMDD}-{uuid4()[:8].upper()}"
- Same ClaimAnalysis response contract as GET /visionguard/api/claims/:claimId

Reference: docs/02_ARCHITECTURE.md (Async Job Pattern section)
Reference: docs/03_API_CONTRACTS.md (Section 5)
Reference: docs/05_TASK_TRACKER.md (Phase 4)
```
