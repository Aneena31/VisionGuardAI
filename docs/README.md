# VisionGuard AI — Documentation Index

This folder is the **Codex bible** for building the VisionGuard AI backend.
Read all documents before writing any code.

## Document Index

| File | Purpose | Read When |
|---|---|---|
| `00_CODEX_KICKSTART.md` | **START HERE** — Codex prompt to bootstrap development | First session |
| `01_PROJECT_OVERVIEW.md` | What the system is, problem, solution, tech stack, folder structure | Orientation |
| `02_ARCHITECTURE.md` | System diagram, pipeline deep-dive, async job pattern, env vars | Design decisions |
| `03_API_CONTRACTS.md` | Every endpoint: URL, request, response schema | Building API |
| `04_DATA_MODEL.md` | Every DB table, SQLAlchemy ORM, ID conventions, cluster definitions | DB + ORM work |
| `05_TASK_TRACKER.md` | Phased build checklist, estimated effort | Project management |
| `06_PIPELINE_REFERENCE.md` | Notebook → module mapping, exact code for each pipeline step | Pipeline implementation |
| `07_UI_GUIDE.md` | Screen-by-screen field mapping, UI quirks, mock → real data checklist | API ↔ UI integration |

## Quick Reference

### Critical Design Decisions
- All API responses use the standard `{ data, meta, error }` envelope
- ML models are trained ONCE during seed, saved as pkl, loaded at API startup
- New claim scoring is async (BackgroundTasks pattern, not Celery)
- AI summary calls OpenAI only for claims with score ≥ 40 (cost control)
- Provider names/specialties are synthetic but deterministic (hash-based from ProviderId)
- Both SQLite (dev) and PostgreSQL (prod) are supported via DATABASE_URL env var

### Key Files to Build First
1. `pipeline/config.py` — all thresholds
2. `pipeline/ingest.py` — load Excel
3. `pipeline/rules.py` — R001–R011
4. `db/models.py` — ORM
5. `db/seed.py` — run everything

### ID Conventions
- Historical claims: `CLM-{raw_claim_id}`
- New scored claims: `TEMP-{YYYYMMDD}-{uuid4[:8]}`
- Providers: `PRV-{last_7_digits_of_ProviderId}`
- Scoring jobs: `JOB-{YYYYMMDD}-{seq:03d}`

### Scoring Weights
- Rules: 35% | Claim Stats: 20% | Provider Stats: 20% | ML: 25%

### Risk Thresholds
- Critical: ≥ 80 | High: ≥ 60 | Medium: ≥ 40 | Low: < 40
