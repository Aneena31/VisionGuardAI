from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from api.services import dashboard_service
from db.database import get_db


router = APIRouter(prefix="/visionguard/api/dashboard", tags=["dashboard"])


@router.get("/overview")
def dashboard_overview(request: Request, db: Session = Depends(get_db)):
    return make_response(dashboard_service.overview(db), request.state.request_id)


@router.post("/export")
def dashboard_export(request: Request):
    return make_response(dashboard_service.export_dashboard(), request.state.request_id)

