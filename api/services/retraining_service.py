from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from api.services import historical_data_service
from db.models import Claim, Notification, PipelineRun, ProviderGold, ScoringJob
from db.seed import _claim_from_row, _provider_gold_payload
from pipeline import config, ml, stats


_retrain_lock = threading.Lock()


def start_sync_retrain(request: Request, db: Session) -> dict[str, Any]:
    if _is_run_active(db):
        latest = _latest_run(db)
        return {
            "accepted": False,
            "status": "running",
            "message": "A model retrain is already running.",
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
        "message": "Model retrain started.",
        "run": _run_payload(run),
        "backgroundTask": _background_retrain,
    }


def run_sync_retrain(db: Session, app: Any, run_id: str) -> None:
    from pipeline.pipeline import run_batch

    run = db.get(PipelineRun, run_id)
    if not run:
        return

    if not _retrain_lock.acquire(blocking=False):
        print(f"[VisionGuard] retrain {run_id} blocked: another retrain is running", flush=True)
        run.status = "failed"
        run.completed_at = datetime.utcnow()
        run.error_message = "Another model retrain is already running."
        db.commit()
        return

    try:
        print(f"[VisionGuard] retrain {run_id} started", flush=True)
        run.status = "running"
        db.commit()

        data_source = config.DEFAULT_DATA_FILE_PATH
        artifacts_path = Path(os.getenv("ARTIFACTS_PATH", str(config.DEFAULT_ARTIFACTS_PATH)))
        if not data_source.exists():
            raise FileNotFoundError(f"Claims data source not found: {data_source}")

        t0 = time.perf_counter()
        print(f"[VisionGuard] retrain {run_id} running pipeline source={data_source}", flush=True)
        claims_df, provider_gold_df, artifacts = run_batch(str(data_source))
        print(
            f"[VisionGuard] retrain {run_id} pipeline completed claims={len(claims_df):,} "
            f"providers={len(provider_gold_df):,} duration={time.perf_counter() - t0:.3f}s",
            flush=True,
        )
        step_t0 = time.perf_counter()
        ml.save_artifacts(
            artifacts["scaler"],
            artifacts["isolation_forest"],
            artifacts["pca"],
            artifacts["ml_features"],
            artifacts_path,
            artifacts["score_stats"],
        )
        print(f"[VisionGuard] retrain {run_id} artifacts saved duration={time.perf_counter() - step_t0:.3f}s", flush=True)

        step_t0 = time.perf_counter()
        db.query(Notification).delete()
        db.query(ScoringJob).delete()
        db.query(ProviderGold).delete()
        db.query(Claim).delete()
        db.commit()
        db.bulk_save_objects([_claim_from_row(row) for _, row in claims_df.iterrows()])
        db.bulk_save_objects([ProviderGold(**_provider_gold_payload(row)) for _, row in provider_gold_df.iterrows()])
        db.commit()
        print(
            f"[VisionGuard] retrain {run_id} database refreshed claims={len(claims_df):,} "
            f"providers={len(provider_gold_df):,} duration={time.perf_counter() - step_t0:.3f}s",
            flush=True,
        )

        step_t0 = time.perf_counter()
        historical_data_service.set_historical_data(claims_df, provider_gold_df, artifacts)
        app.state.artifacts = ml.load_artifacts(artifacts_path)
        app.state.population_stats = stats.get_population_stats_from_frame(claims_df)
        print(f"[VisionGuard] retrain {run_id} app state refreshed duration={time.perf_counter() - step_t0:.3f}s", flush=True)

        run = db.get(PipelineRun, run_id)
        run.status = "completed"
        run.claims_processed = int(len(claims_df))
        run.claims_failed = 0
        run.completed_at = datetime.utcnow()
        run.duration_seconds = float(time.perf_counter() - t0)
        run.error_message = None
        db.commit()
        print(
            f"[VisionGuard] retrain {run_id} completed claims={run.claims_processed:,} "
            f"duration={run.duration_seconds:.3f}s",
            flush=True,
        )
    except Exception as exc:
        print(f"[VisionGuard] retrain {run_id} failed error={exc}", flush=True)
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
