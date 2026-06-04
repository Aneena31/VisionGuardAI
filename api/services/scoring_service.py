from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from api.services.claim_service import build_single_claim_analysis
from db.database import SessionLocal
from db.models import Notification, ScoringJob
from pipeline.pipeline import run_single


STAGES = [
    ("validate", "Validating Format...", 15),
    ("rules", "Rule Engine Analysis...", 35),
    ("statistics", "Statistical Profiling...", 55),
    ("ml", "ML Outlier Detection...", 75),
    ("cluster", "Assigning Behavioral Clusters...", 85),
    ("summary", "Generating AI Summary...", 95),
]


def create_job(db: Session, source_type: str, claim_input: dict) -> ScoringJob:
    now = datetime.utcnow()
    job = ScoringJob(
        id=f"JOB-{now:%Y%m%d}-{str(uuid4())[:6].upper()}",
        status="queued",
        source_type=source_type,
        progress_percent=0,
        active_stage="Queued",
        claim_input_json=json.dumps(claim_input),
        generated_claim_id=f"TEMP-{now:%Y%m%d}-{str(uuid4())[:8].upper()}",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def job_status_payload(job: ScoringJob) -> dict:
    return {
        "jobId": job.id,
        "status": job.status,
        "progressPercent": job.progress_percent or 0,
        "activeStage": job.active_stage,
        "stages": _stage_payload(job.progress_percent or 0, job.status),
    }


def run_pipeline_task(job_id: str, artifacts: dict, population_stats: dict) -> None:
    db = SessionLocal()
    try:
        job = db.get(ScoringJob, job_id)
        if not job:
            return
        _update_job(db, job, "validating", 15, "Validating Format...")
        claim_input = json.loads(job.claim_input_json or "{}")
        claim_input["ClaimId"] = job.generated_claim_id

        _update_job(db, job, "processing", 35, "Rule Engine Analysis...")
        _update_job(db, job, "processing", 55, "Statistical Profiling...")
        _update_job(db, job, "processing", 75, "ML Outlier Detection...")
        result = run_single(claim_input, artifacts, population_stats)
        result["ClaimId"] = job.generated_claim_id

        _update_job(db, job, "processing", 85, "Assigning Behavioral Clusters...")
        _update_job(db, job, "processing", 95, "Generating AI Summary...")
        analysis = build_single_claim_analysis(result)
        job.status = "completed"
        job.progress_percent = 100
        job.active_stage = "Scoring Complete"
        job.result_json = json.dumps(analysis)
        job.completed_at = datetime.utcnow()
        if result.get("Final_Risk_Level") == "Critical":
            db.add(
                Notification(
                    id=f"NTF-{str(uuid4())[:8].upper()}",
                    type="job_completed",
                    title="Critical claim scored",
                    message=f"New claim {job.generated_claim_id} scored Critical.",
                    related_claim_id=job.generated_claim_id,
                )
            )
        db.commit()
    except Exception as exc:
        job = db.get(ScoringJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.active_stage = "Pipeline failed"
            db.commit()
    finally:
        db.close()


def assign_siu(db: Session, job: ScoringJob) -> dict:
    job.assigned_queue = "SIU"
    job.assigned_at = datetime.utcnow()
    db.add(
        Notification(
            id=f"NTF-{str(uuid4())[:8].upper()}",
            type="claim_flagged",
            title="Scored claim assigned",
            message=f"Scoring job {job.id} was assigned to the SIU queue.",
            related_claim_id=job.generated_claim_id,
        )
    )
    db.commit()
    return {
        "jobId": job.id,
        "assignedQueue": "SIU",
        "assignedAt": job.assigned_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "Investigating",
    }


def _update_job(db: Session, job: ScoringJob, status: str, progress: int, stage: str) -> None:
    job.status = status
    job.progress_percent = progress
    job.active_stage = stage
    db.commit()
    db.refresh(job)


def _stage_payload(progress: int, status: str) -> list[dict]:
    rows = []
    for code, label, threshold in STAGES:
        if status == "failed":
            stage_status = "pending"
        elif progress >= threshold:
            stage_status = "completed"
        elif progress > 0 and progress < threshold and not any(progress < prior[2] for prior in STAGES if prior[2] < threshold):
            stage_status = "processing"
        else:
            stage_status = "pending"
        rows.append({"code": code, "label": label, "status": stage_status, "progressPercent": threshold})
    return rows
