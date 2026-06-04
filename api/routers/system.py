from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from db.database import get_db
from db.models import PipelineRun


router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def system_status(request: Request, db: Session = Depends(get_db)):
    latest = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    return make_response(
        {
            "modelAi": "ONLINE" if request.app.state.artifacts is not None else "OFFLINE",
            "pipeline": "SYNCED" if latest and latest.status == "completed" else "STALE",
            "lastSuccessfulRunAt": latest.completed_at.isoformat() + "Z" if latest and latest.completed_at else None,
        },
        request.state.request_id,
    )

