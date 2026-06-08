from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
import pandas as pd
from sqlalchemy.orm import Session

from db.models import Claim, Notification, PipelineRun, ProviderGold
from pipeline import config, ingest, ml, stats


_retrain_lock = threading.Lock()


def start_sync_retrain(request: Request, db: Session) -> dict[str, Any]:
    if _is_run_active(db):
        latest = _latest_run(db)
        return {
            "accepted": False,
            "status": "running",
            "message": "A claims sync is already running.",
            "run": _run_payload(latest) if latest else None,
        }

    started_at = datetime.utcnow()
    run_id = f"RUN-{started_at:%Y%m%d%H%M%S}"
    run = PipelineRun(id=run_id, status="queued", started_at=started_at, claims_processed=0, claims_failed=0)
    db.add(run)
    db.commit()

    app = request.app

    def _background_retrain() -> None:
        from db.database import SessionLocal

        bg_db = SessionLocal()
        try:
            run_sync_retrain(bg_db, app, run_id)
        finally:
            bg_db.close()

    return {
        "accepted": True,
        "status": "queued",
        "message": "Claims sync started.",
        "run": _run_payload(run),
        "backgroundTask": _background_retrain,
    }


def run_sync_retrain(db: Session, app: Any, run_id: str) -> None:
    from db.seed import _claim_from_row, _provider_gold_payload
    from pipeline.pipeline import run_batch_dataframe

    run = db.get(PipelineRun, run_id)
    if not run:
        return

    if not _retrain_lock.acquire(blocking=False):
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        run.error_message = "Another historical sync and retrain is already running."
        db.commit()
        return

    try:
        run.status = "running"
        db.commit()

        data_source = config.DEFAULT_DATA_FILE_PATH
        artifacts_path = Path(os.getenv("ARTIFACTS_PATH", str(config.DEFAULT_ARTIFACTS_PATH)))
        if not data_source.exists():
            raise FileNotFoundError(f"Claims data source not found: {data_source}")

        t0 = time.perf_counter()
        imported_claims_df = ingest.load_and_clean_source(str(data_source))

        db.query(Notification).delete()
        db.query(ProviderGold).delete()
        db.query(Claim).delete()
        db.commit()

        db.bulk_save_objects([_claim_from_row(row) for _, row in imported_claims_df.iterrows()])
        db.commit()

        training_df = _claims_to_training_frame(db)
        claims_df, provider_gold_df, artifacts = run_batch_dataframe(training_df)
        ml.save_artifacts(
            artifacts["scaler"],
            artifacts["isolation_forest"],
            artifacts["pca"],
            artifacts["ml_features"],
            artifacts_path,
            artifacts["score_stats"],
        )

        db.query(ProviderGold).delete()
        db.query(Claim).delete()
        db.commit()

        db.bulk_save_objects([_claim_from_row(row) for _, row in claims_df.iterrows()])
        db.bulk_save_objects([ProviderGold(**_provider_gold_payload(row)) for _, row in provider_gold_df.iterrows()])
        db.commit()

        app.state.artifacts = ml.load_artifacts(artifacts_path)
        app.state.population_stats = stats.get_population_stats(db)

        run = db.get(PipelineRun, run_id)
        run.status = "completed"
        run.claims_processed = int(len(claims_df))
        run.claims_failed = 0
        run.completed_at = datetime.utcnow()
        run.duration_seconds = float(time.perf_counter() - t0)
        run.error_message = None
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(PipelineRun, run_id)
        if run:
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error_message = str(exc)
            db.commit()
    finally:
        _retrain_lock.release()


def latest_sync_retrain(db: Session) -> dict[str, Any] | None:
    run = _latest_run(db)
    return _run_payload(run) if run else None


def _is_run_active(db: Session) -> bool:
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.status.in_(["queued", "running"]))
        .order_by(PipelineRun.started_at.desc())
        .first()
        is not None
    )


def _latest_run(db: Session) -> PipelineRun | None:
    return db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()


def _claims_to_training_frame(db: Session) -> pd.DataFrame:
    claims = db.query(Claim).order_by(Claim.row_id.asc(), Claim.id.asc()).all()
    return pd.DataFrame(
        [
            {
                "ClaimId": claim.raw_claim_id or claim.row_id,
                "AdjustmentVersion": claim.adjustment_version,
                "LineNumber": claim.line_number,
                "ProviderId": claim.provider_id,
                "ProcedureCode": claim.procedure_code,
                "ProcedureDesc": claim.procedure_desc,
                "ServiceCategoryName": claim.service_category_name,
                "BenefitCategoryName": claim.benefit_category_name,
                "BenefitType": claim.benefit_type,
                "ServiceMonth": claim.service_date,
                "MemberId": claim.member_id,
                "MemberAge": claim.member_age,
                "Gender": claim.member_gender,
                "SubscriberId": claim.subscriber_id,
                "GroupId": claim.group_id,
                "AmtCharged": claim.amt_charged,
                "PaidAmount": claim.paid_amount,
                "AllowedAmount": claim.amt_allowed,
                "AllowedUnits": claim.allowed_units,
                "UnitsUsed": claim.units_used,
                "UtilizationPctAmt": claim.utilization_pct_amt,
            }
            for claim in claims
        ]
    )


def _run_payload(run: PipelineRun | None) -> dict[str, Any] | None:
    if not run:
        return None
    return {
        "id": run.id,
        "status": run.status,
        "claimsProcessed": run.claims_processed or 0,
        "claimsFailed": run.claims_failed or 0,
        "startedAt": _iso(run.started_at),
        "completedAt": _iso(run.completed_at),
        "durationSeconds": run.duration_seconds,
        "errorMessage": run.error_message,
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None
