# VisionGuard AI — Project Overview

## What Is This?

VisionGuard AI is a vision insurance claims fraud detection platform built for Special Investigations Unit (SIU) analysts. It ingests raw vision claims (V-codes, eye exams, frames, lenses), runs a multi-layer detection pipeline, and surfaces SIU-ready fraud scores with human-readable explanations.

The system is designed to replace manual triage with an automated, explainable AI workflow that still keeps a human in the loop for final decisions.

---

## Problem Statement

Vision insurance fraud — upcoding premium lenses, phantom billing, frame upcoding, unbundling — is low-dollar-per-claim but high-volume. Manual review is too slow and misses pattern-level fraud that only appears when you look across a provider's full billing history. Current tools produce scores but not reasons, making SIU adoption difficult.

---

## Solution Architecture (High Level)

```
Raw Claims (Excel / x12_837 / JSON / CSV)
        │
        ▼
  Data Ingestion & Cleaning
        │
        ▼
  ┌─────────────────────────────────────┐
  │         Detection Pipeline          │
  │                                     │
  │  1. Rule Engine (R001–R011)         │
  │     Deterministic V-code rules      │
  │                                     │
  │  2. Statistical Outlier Engine      │
  │     Z-scores at claim + provider    │
  │                                     │
  │  3. Unsupervised ML                 │
  │     Isolation Forest + PCA Error    │
  │                                     │
  │  4. Final Combined Scoring          │
  │     Weighted composite 0–100        │
  │                                     │
  │  5. AI Summary (LLM)               │
  │     ChatOpenAI explainability layer │
  └─────────────────────────────────────┘
        │
        ▼
  Provider Aggregation (Gold Table)
        │
        ▼
  FastAPI Backend (REST)
        │
        ▼
  VisionGuard React UI
  (Executive Dashboard / Claims Explorer /
   Provider Intelligence / New Claim Scoring)
```

---

## Scope of This POC

| Area | In Scope | Out of Scope |
|---|---|---|
| Claims data | 10,000-row synthetic Excel | Real EDI/x12 integration |
| Fraud types | V-code upcoding, high-cost, billing ratio, young member abuse | CPT, J-code, modifier rules |
| ML | Isolation Forest + PCA (sklearn) | Deep learning, LLM fine-tuning |
| AI Summary | ChatOpenAI API call per scored claim | On-premise LLM |
| Auth | API key header (dev), or none for POC | OAuth2, RBAC |
| Storage | SQLite (dev) / PostgreSQL (prod-ready) | Data warehouse, Delta Lake |
| Deployment | Local / Docker | Cloud infra, Kubernetes |

---

## Key Personas

**SIU Analyst** — Reviews flagged claims, investigates providers, assigns cases. Needs clear fraud reasoning, not just scores.

**SIU Manager / Executive** — Monitors aggregate fraud trends, KPIs, portfolio risk. Uses the Executive Dashboard.

**Data Scientist / ML Engineer** — Maintains the pipeline, tunes thresholds, adds new rules. Interacts with the notebook and pipeline code.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Pipeline / ML | Python, pandas, scikit-learn, numpy |
| AI Summary | OpenAI `gpt-4o` via `openai` SDK |
| Backend API | FastAPI + Uvicorn |
| Database | SQLite (dev), PostgreSQL (prod) |
| ORM | SQLAlchemy |
| Frontend | React + TypeScript + Tailwind CSS |
| Data file | Excel (.xlsx), 10k synthetic rows |
| Package mgmt | pip + requirements.txt |
| Dev tooling | Jupyter Notebook (pipeline dev), VS Code |

---

## Folder Structure (Target)

```
visionguard/
├── docs/                        ← This folder (Codex bible)
├── data/
│   └── Sample_Data_for_ML.xlsx  ← Source truth
├── pipeline/
│   ├── ingest.py                ← Load + clean raw data
│   ├── rules.py                 ← Rule engine R001–R011
│   ├── stats.py                 ← Statistical outlier engine
│   ├── ml.py                    ← Isolation Forest + PCA
│   ├── scoring.py               ← Final combined score
│   ├── narrative.py             ← Rule + ML narratives
│   ├── similarity.py            ← Similar claims engine
│   ├── ai_summary.py            ← ChatOpenAI explainability
│   └── pipeline.py              ← Orchestrator (run all steps)
├── db/
│   ├── models.py                ← SQLAlchemy ORM models
│   ├── seed.py                  ← Seed DB from Excel run
│   └── database.py              ← DB session / engine
├── api/
│   ├── main.py                  ← FastAPI app entry
│   ├── routers/
│   │   ├── dashboard.py
│   │   ├── claims.py
│   │   ├── providers.py
│   │   ├── scoring.py
│   │   ├── search.py
│   │   ├── notifications.py
│   │   └── system.py
│   ├── schemas/                 ← Pydantic request/response models
│   └── services/                ← Business logic layer
├── visionguard-ui/              ← Existing React frontend (unchanged)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Data Flow Summary

### Historical Claims (Batch — runs once at seed time)
1. Load `Sample_Data_for_ML.xlsx` → `df_raw`
2. Clean + derive features (`AmtAllowed`, `Units`, `PatientAge`, `BilledAmountToAllowedRatio`)
3. Apply rule engine → 11 boolean flags + `Rule_Score_Total`
4. Apply statistical engine → Z-scores + `Claim_Stat_Score` + `Provider_Stat_Score`
5. Apply ML engine → `IF_Score`, `PCA_Recon_Error`, `ML_Anomaly_Score`
6. Apply final scoring → `Final_Combined_Score`, `Final_Risk_Level`, `Final_Fraud_Type`
7. Generate AI summary via ChatOpenAI
8. Aggregate to `provider_gold` table
9. Persist everything to database
10. API serves pre-computed results

### New Claim Scoring (Real-time — per API request)
1. Accept claim via file upload or JSON
2. Auto-generate `ClaimId`, `row_id`
3. Run same pipeline steps 2–7 above in-process
4. Return `ClaimAnalysis` payload (matches same schema as historical claims)
5. Optionally assign to SIU queue

---

## Non-Functional Requirements (POC)

- Pipeline seed run completes in < 5 minutes for 10k rows
- New claim scoring completes in < 30 seconds (API responds with job status, polls for result)
- API response time < 500ms for all read endpoints
- All fraud scores are explainable (rule narrative + AI summary always present)
- No PII in logs
