from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from api.services import provider_service
from db.database import get_db
from typing import Optional


router = APIRouter(prefix="/visionguard/providers", tags=["providers"])


@router.get("")
def list_providers(
    request: Request,
    search: Optional[str] = None,
    riskLevel: Optional[str] = None,
    page: int = 1,
    pageSize: int = Query(50, le=100),
    sortBy: str = "riskScore",
    sortDir: str = "desc",
    db: Session = Depends(get_db),
):
    data = provider_service.list_providers(
        db, search=search, risk_level=riskLevel, page=page, page_size=pageSize, sort_by=sortBy, sort_dir=sortDir
    )
    return make_response(data, request.state.request_id)


@router.get("/{provider_id}")
def get_provider(provider_id: str, request: Request, db: Session = Depends(get_db)):
    data = provider_service.get_provider_detail(db, provider_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Provider with ID {provider_id} was not found.")
    return make_response(data, request.state.request_id)

