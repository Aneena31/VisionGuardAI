from __future__ import annotations

import io
import json
from typing import Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from api.schemas.scoring import ScoringJobCreate
from api.services import scoring_service
from db.database import get_db
from db.models import ScoringJob
from typing import Optional


router = APIRouter(prefix="/visionguard/api/scoring", tags=["scoring"])


@router.post("/jobs")
async def create_scoring_job(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    source_type, claim_input = await _extract_claim_input(request, file)
    if request.app.state.artifacts is None:
        raise HTTPException(status_code=503, detail="ML artifacts are not loaded. Run db/seed.py first.")
    job = scoring_service.create_job(db, source_type, claim_input)
    background_tasks.add_task(
        scoring_service.run_pipeline_task,
        job.id,
        request.app.state.artifacts,
        request.app.state.population_stats,
    )
    return make_response(
        {
            "jobId": job.id,
            "status": job.status,
            "sourceType": job.source_type,
            "submittedAt": job.submitted_at.isoformat() + "Z",
        },
        request.state.request_id,
    )


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.get(ScoringJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Scoring job {job_id} was not found.")
    return make_response(scoring_service.job_status_payload(job), request.state.request_id)


@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.get(ScoringJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Scoring job {job_id} was not found.")
    if job.status != "completed" or not job.result_json:
        raise HTTPException(status_code=409, detail=f"Scoring job {job_id} is not completed.")
    return make_response(json.loads(job.result_json), request.state.request_id)


@router.post("/jobs/{job_id}/assign-siu")
def assign_siu(job_id: str, request: Request, db: Session = Depends(get_db)):
    job = db.get(ScoringJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Scoring job {job_id} was not found.")
    return make_response(scoring_service.assign_siu(db, job), request.state.request_id)


async def _extract_claim_input(request: Request, file: Optional[UploadFile]) -> tuple[str, dict]:
    if file:
        raw = await file.read()
        name = (file.filename or "").lower()
        if name.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(raw))
            return "csv", df.iloc[0].to_dict()
        if name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(raw))
            return "x12_837", df.iloc[0].to_dict()
        if name.endswith(".json"):
            payload = json.loads(raw.decode("utf-8"))
            claim = payload[0] if isinstance(payload, list) else payload.get("claim", payload)
            return "json", claim
        raise HTTPException(status_code=422, detail="Unsupported file type. Use .xlsx, .csv, or .json.")

    payload = await request.json()
    parsed = ScoringJobCreate(**payload)
    return parsed.sourceType, parsed.claim.model_dump()
