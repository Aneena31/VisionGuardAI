# VisionGuard AI Backend

FastAPI backend, fraud detection pipeline, SQLAlchemy database layer, and seed script for the VisionGuard AI vision insurance fraud detection POC.

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Place the source workbook at:

```text
data/Sample_Data_for_ML.xlsx
```

## Seed The Database

```powershell
python db\seed.py
```

The seed script runs the batch pipeline, saves ML artifacts to `artifacts/`, and persists claims plus provider gold records to the configured database.

## Run The API

```powershell
uvicorn api.main:app --reload
```

Default API URL:

```text
http://localhost:8000
```

All API responses use the documented envelope:

```json
{ "data": {}, "meta": { "requestId": "...", "generatedAt": "..." }, "error": null }
```
