from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from api.services.claim_service import build_single_claim_analysis
from api.services.historical_data_service import get_historical_data
from db.database import SessionLocal
from db.models import Claim, Notification, ScoringJob
from pipeline.pipeline import run_single


STAGES = [
    ("validate", "Checking claim details...", 15),
    ("rules", "Running rules engine...", 35),
    ("statistics", "Comparing with historical claims...", 55),
    ("ml", "Looking for unusual payment patterns...", 75),
    ("cluster", "Matching to known issue types...", 85),
    ("summary", "Preparing review summary...", 95),
]


def create_job(db: Session, source_type: str, claim_input: dict) -> ScoringJob:
    now = datetime.utcnow()
    job = ScoringJob(
        id=f"JOB-{now:%Y%m%d}-{str(uuid4())[:6].upper()}",
        status="queued",
        source_type=source_type,
        progress_percent=0,
        active_stage="Queued for review",
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
        _update_job(db, job, "validating", 15, "Checking claim details...")
        claim_input = json.loads(job.claim_input_json or "{}")
        claim_input["ClaimId"] = job.generated_claim_id

        _update_job(db, job, "processing", 35, "Running rules engine...")
        _update_job(db, job, "processing", 55, "Comparing with historical claims...")
        _update_job(db, job, "processing", 75, "Looking for unusual payment patterns...")
        result = run_single(claim_input, artifacts, population_stats, _historical_claims_frame(db))
        result["ClaimId"] = job.generated_claim_id

        _update_job(db, job, "processing", 85, "Matching to known issue types...")
        _update_job(db, job, "processing", 95, "Preparing review summary...")
        analysis = build_single_claim_analysis(result)
        job.status = "completed"
        job.progress_percent = 100
        job.active_stage = "Review complete"
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
            job.active_stage = "Review failed"
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


def _historical_claims_frame(db: Session) -> pd.DataFrame | None:
    rows = db.query(Claim).all()
    if rows:
        return pd.DataFrame(
            [
                {
                    "ClaimRecordId": claim.id,
                    "ClaimId": claim.raw_claim_id,
                    "ProviderId": claim.provider_id,
                    "ProviderName": claim.provider_name,
                    "ProcedureCode": claim.procedure_code,
                    "ProcedureDesc": claim.procedure_desc,
                    "BenefitType": claim.benefit_type,
                    "ServiceCategoryName": claim.service_category_name,
                    "BenefitCategoryName": claim.benefit_category_name,
                    "ServiceMonth": claim.service_date,
                    "AmtAllowed": claim.amt_allowed,
                    "AmtCharged": claim.amt_charged,
                    "Units": claim.units_used,
                    "PatientAge": claim.member_age,
                    "BilledAmountToAllowedRatio": claim.billed_amount_to_allowed_ratio,
                    "Rule_Score_Norm": claim.rule_score_norm,
                    "Claim_Stat_Score_Norm": claim.claim_stat_score_norm,
                    "Provider_Stat_Score_Norm": claim.provider_stat_score_norm,
                    "ML_Anomaly_Score_Norm": claim.ml_anomaly_score_norm,
                    "Final_Combined_Score": claim.final_combined_score,
                    "Final_Risk_Level": claim.final_risk_level,
                    "Final_Fraud_Type": claim.final_fraud_type,
                    "cluster_id": claim.cluster_id,
                    "status": claim.status,
                }
                for claim in rows
            ]
        )

    try:
        return get_historical_data().claims_df
    except Exception:
        return None


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
