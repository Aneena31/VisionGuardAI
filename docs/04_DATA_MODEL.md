# VisionGuard AI — Data Model & Database Schema

## Overview

The database serves two purposes:
1. Store pre-computed pipeline results from the batch seed run (historical claims, provider gold)
2. Track real-time scoring jobs and their results

All models are defined as SQLAlchemy ORM classes in `db/models.py`.

---

## Tables

### `claims`

Stores every claim row from the batch pipeline run, plus all computed scores and narratives.

```sql
CREATE TABLE claims (
    -- Identity
    id                          VARCHAR PRIMARY KEY,   -- e.g. "CLM-79518297" (generated from raw ClaimId)
    raw_claim_id                INTEGER,               -- Original ClaimId from Excel
    row_id                      INTEGER,               -- 1-based row index

    -- Provider / Member
    provider_id                 VARCHAR,               -- Formatted "PRV-{ProviderId}"
    provider_name               VARCHAR,               -- Populated later or from lookup
    member_id                   VARCHAR,               -- Formatted "MEM-{MemberId}"
    member_age                  INTEGER,
    member_gender               VARCHAR,
    subscriber_id               VARCHAR,
    group_id                    VARCHAR,

    -- Claim details
    procedure_code              VARCHAR,               -- V-code or CPT
    procedure_desc              VARCHAR,               -- Human-readable description (lookup or blank)
    benefit_type                VARCHAR,               -- Exam | Lens | Frame | Contact | Other
    service_category_name       VARCHAR,
    benefit_category_name       VARCHAR,
    service_date                DATE,                  -- ServiceMonth parsed
    service_year                INTEGER,
    adjustment_version          INTEGER,
    line_number                 INTEGER,

    -- Amounts
    amt_charged                 FLOAT,
    amt_allowed                 FLOAT,
    paid_amount                 FLOAT,
    allowed_units               FLOAT,
    units_used                  FLOAT,
    utilization_pct_amt         FLOAT,
    billed_amount_to_allowed_ratio FLOAT,

    -- Rule Engine Output
    r001_material_upcoding      BOOLEAN DEFAULT FALSE,
    r002_material_upcoding_lens BOOLEAN DEFAULT FALSE,
    r003_polycarb               BOOLEAN DEFAULT FALSE,
    r004_frame_upcoding         BOOLEAN DEFAULT FALSE,
    r005_sunglasses             BOOLEAN DEFAULT FALSE,
    r006_highcost_frames        BOOLEAN DEFAULT FALSE,
    r007_highcost_lenses        BOOLEAN DEFAULT FALSE,
    r008_highcost_materials     BOOLEAN DEFAULT FALSE,
    r009_high_billed_ratio      BOOLEAN DEFAULT FALSE,
    r010_high_units             BOOLEAN DEFAULT FALSE,
    r011_young_member           BOOLEAN DEFAULT FALSE,
    rule_flag_count             INTEGER DEFAULT 0,
    rule_score_total            FLOAT DEFAULT 0,
    rule_narrative              TEXT,

    -- Statistical Scores
    z_allowed_amount            FLOAT,
    z_units                     FLOAT,
    z_billed_to_allowed         FLOAT,
    claim_stat_score            FLOAT,
    provider_stat_score         FLOAT,
    stat_narrative              TEXT,

    -- ML Scores
    if_score                    FLOAT,
    if_score_norm               FLOAT,
    pca_recon_error             FLOAT,
    pca_score_norm              FLOAT,
    ml_anomaly_score            FLOAT,
    ml_anomaly_flag             BOOLEAN DEFAULT FALSE,
    ml_anomaly_narrative        TEXT,
    ml_flag                     BOOLEAN DEFAULT FALSE,

    -- Final Scoring
    rule_score_norm             FLOAT,
    claim_stat_score_norm       FLOAT,
    provider_stat_score_norm    FLOAT,
    ml_anomaly_score_norm       FLOAT,
    final_combined_score        FLOAT,
    final_risk_level            VARCHAR,               -- Low | Medium | High | Critical
    final_fraud_type            VARCHAR,
    final_fraud_reason          TEXT,
    final_narrative             TEXT,

    -- AI Summary
    ai_summary                  TEXT,                  -- JSON string: {summary, riskReasoning, recommendation}
    ai_summary_generated        BOOLEAN DEFAULT FALSE,

    -- Cluster Assignment
    cluster_id                  VARCHAR,               -- e.g. "CL-01"

    -- Similar Claims
    similar_claim_ids           TEXT,                  -- JSON array of row IDs

    -- Status / Workflow
    status                      VARCHAR DEFAULT 'Pending', -- Pending | Flagged | Cleared | Investigating
    flagged_at                  TIMESTAMP,
    assigned_to                 VARCHAR,

    -- Metadata
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_claims_provider_id ON claims(provider_id);
CREATE INDEX idx_claims_risk_level ON claims(final_risk_level);
CREATE INDEX idx_claims_procedure_code ON claims(procedure_code);
CREATE INDEX idx_claims_service_date ON claims(service_date);
CREATE INDEX idx_claims_final_score ON claims(final_combined_score DESC);
```

---

### `provider_gold`

Aggregated provider-level intelligence. Built from `claims` after batch pipeline.

```sql
CREATE TABLE provider_gold (
    id                          VARCHAR PRIMARY KEY,   -- "PRV-{ProviderId}"
    raw_provider_id             VARCHAR,               -- Original ProviderId

    -- Provider metadata (populated from lookup or synthetic)
    name                        VARCHAR,
    specialty                   VARCHAR,
    city                        VARCHAR,
    state                       VARCHAR,

    -- Aggregate metrics
    total_claims                INTEGER,
    total_allowed               FLOAT,
    avg_allowed                 FLOAT,
    avg_units                   FLOAT,
    high_risk_claims            INTEGER,
    high_risk_ratio             FLOAT,

    -- Average pipeline scores
    avg_final_score             FLOAT,
    avg_rule_score              FLOAT,
    avg_stat_score              FLOAT,
    avg_prov_stat_score         FLOAT,
    avg_ml_score                FLOAT,

    -- Provider Risk
    provider_risk_score         FLOAT,
    provider_risk_level         VARCHAR,               -- Low | Medium | High | Critical
    provider_narrative          TEXT,

    -- AI Summary (provider-level)
    ai_pattern_deviation        TEXT,
    ai_velocity_indicator       TEXT,
    ai_recommendation           TEXT,

    -- Metadata
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_provider_gold_risk_score ON provider_gold(provider_risk_score DESC);
CREATE INDEX idx_provider_gold_risk_level ON provider_gold(provider_risk_level);
```

---

### `scoring_jobs`

Tracks real-time scoring requests from the New Claim Scoring screen.

```sql
CREATE TABLE scoring_jobs (
    id                          VARCHAR PRIMARY KEY,   -- "JOB-{YYYYMMDD}-{uuid4[:8]}"
    status                      VARCHAR DEFAULT 'queued', -- queued | validating | processing | completed | failed
    source_type                 VARCHAR,               -- manual | csv | json | x12_837
    progress_percent            INTEGER DEFAULT 0,
    active_stage                VARCHAR,

    -- Submitted claim data
    claim_input_json            TEXT,                  -- raw JSON of submitted claim

    -- Generated claim ID
    generated_claim_id          VARCHAR,               -- "TEMP-{YYYYMMDD}-{uuid4[:8]}"

    -- Result (stored as JSON blob once completed)
    result_json                 TEXT,                  -- full ClaimAnalysis JSON

    -- Error tracking
    error_message               TEXT,

    -- Timestamps
    submitted_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at                TIMESTAMP,

    -- Assignment
    assigned_queue              VARCHAR,
    assigned_at                 TIMESTAMP,
    assigned_to                 VARCHAR
);

CREATE INDEX idx_scoring_jobs_status ON scoring_jobs(status);
```

---

### `notifications`

Bell icon notifications for SIU workflow events.

```sql
CREATE TABLE notifications (
    id                          VARCHAR PRIMARY KEY,   -- "NTF-{uuid4[:8]}"
    type                        VARCHAR,               -- claim_flagged | provider_alert | job_completed
    title                       VARCHAR,
    message                     TEXT,
    related_claim_id            VARCHAR,
    related_provider_id         VARCHAR,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read                        BOOLEAN DEFAULT FALSE
);
```

---

### `pipeline_runs`

Tracks batch pipeline execution history.

```sql
CREATE TABLE pipeline_runs (
    id                          VARCHAR PRIMARY KEY,   -- "RUN-{YYYYMMDD}-{seq}"
    status                      VARCHAR,               -- running | completed | failed
    claims_processed            INTEGER,
    claims_failed               INTEGER,
    started_at                  TIMESTAMP,
    completed_at                TIMESTAMP,
    duration_seconds            FLOAT,
    error_message               TEXT
);
```

---

## SQLAlchemy ORM (Python)

```python
# db/models.py
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Claim(Base):
    __tablename__ = "claims"
    id = Column(String, primary_key=True)
    raw_claim_id = Column(Integer)
    provider_id = Column(String, index=True)
    member_id = Column(String)
    member_age = Column(Integer)
    procedure_code = Column(String, index=True)
    procedure_desc = Column(String)
    benefit_type = Column(String)
    service_category_name = Column(String)
    benefit_category_name = Column(String)
    service_date = Column(Date)
    amt_charged = Column(Float)
    amt_allowed = Column(Float)
    units_used = Column(Float)
    billed_amount_to_allowed_ratio = Column(Float)
    # ... rule flags ...
    rule_score_total = Column(Float)
    rule_narrative = Column(Text)
    claim_stat_score = Column(Float)
    provider_stat_score = Column(Float)
    ml_anomaly_score = Column(Float)
    if_score_norm = Column(Float)
    pca_score_norm = Column(Float)
    final_combined_score = Column(Float, index=True)
    final_risk_level = Column(String, index=True)
    final_fraud_type = Column(String)
    final_fraud_reason = Column(Text)
    ai_summary = Column(Text)
    cluster_id = Column(String)
    similar_claim_ids = Column(Text)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProviderGold(Base):
    __tablename__ = "provider_gold"
    id = Column(String, primary_key=True)
    raw_provider_id = Column(String)
    name = Column(String)
    specialty = Column(String)
    city = Column(String)
    state = Column(String)
    total_claims = Column(Integer)
    total_allowed = Column(Float)
    avg_allowed = Column(Float)
    high_risk_claims = Column(Integer)
    high_risk_ratio = Column(Float)
    avg_final_score = Column(Float)
    avg_ml_score = Column(Float)
    provider_risk_score = Column(Float, index=True)
    provider_risk_level = Column(String, index=True)
    provider_narrative = Column(Text)
    ai_pattern_deviation = Column(Text)
    ai_velocity_indicator = Column(Text)
    ai_recommendation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScoringJob(Base):
    __tablename__ = "scoring_jobs"
    id = Column(String, primary_key=True)
    status = Column(String, default="queued", index=True)
    source_type = Column(String)
    progress_percent = Column(Integer, default=0)
    active_stage = Column(String)
    claim_input_json = Column(Text)
    generated_claim_id = Column(String)
    result_json = Column(Text)
    error_message = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    assigned_queue = Column(String)
    assigned_at = Column(DateTime)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True)
    type = Column(String)
    title = Column(String)
    message = Column(Text)
    related_claim_id = Column(String)
    related_provider_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)
```

---

## ID Generation Conventions

| Entity | Format | Example |
|---|---|---|
| Claim (historical) | `CLM-{raw_claim_id}` | `CLM-79518297` |
| Claim (new scoring) | `TEMP-{YYYYMMDD}-{uuid4[:8]}` | `TEMP-20260604-a1b2c3d4` |
| Provider | `PRV-{raw_provider_id[-7:]}` | `PRV-1621096` |
| Member | `MEM-{raw_member_id[-7:]}` | `MEM-0204162` |
| Scoring Job | `JOB-{YYYYMMDD}-{seq:03d}` | `JOB-20260604-001` |
| Pipeline Run | `RUN-{YYYYMMDD}-{seq:03d}` | `RUN-20260604-001` |
| Notification | `NTF-{uuid4[:8]}` | `NTF-a1b2c3d4` |
| Cluster | `CL-{02d}` | `CL-01`, `CL-03` |

---

## Cluster Definitions (Static Lookup)

Clusters are not computed by the pipeline — they are a static reference table assigned based on fraud type patterns. For the POC, define them as a dict in code or a small seed table.

```python
CLUSTER_DEFINITIONS = {
    "CL-01": {
        "name": "Phantom Billing",
        "description": "Services billed for which no encounter occurred.",
        "commonProcedures": ["V2784", "V2118"],
        "avgFraudScore": 88,
    },
    "CL-02": {
        "name": "Upcoding - Exam",
        "description": "Billing for a more complex exam than was performed.",
        "commonProcedures": ["92004", "92014"],
        "avgFraudScore": 75,
    },
    "CL-03": {
        "name": "Unbundling - Glaucoma Screening",
        "description": "Separating bundled screening procedures into individual components.",
        "commonProcedures": ["92250", "92134"],
        "avgFraudScore": 92,
    },
    "CL-00": {
        "name": "N/A",
        "description": "No behavioral cluster assigned.",
        "commonProcedures": [],
        "avgFraudScore": 0,
    }
}
```

**Cluster assignment logic:** Map `Final_Fraud_Type` to cluster:
- `"Rule-Based Upcoding / High-Cost"` → `CL-02`
- `"ML Pattern Anomaly"` + V-code pattern → `CL-01`
- `"Provider Outlier Behavior"` + unbundling signal → `CL-03`
- Everything else → `CL-00`

---

## Seed Run Output

After `python db/seed.py`:

```
DB seeded successfully.
Claims persisted:     10,000
Providers persisted:  ~9,500 (unique ProviderId count)
AI summaries generated: ~3,100 (Medium+ risk only)
Duration: ~4 min 20 sec
```
