from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from api.services import claim_service, retraining_service
from db.database import get_db


router = APIRouter(prefix="/visionguard/claims", tags=["claims"])


@router.get("")
def list_claims(
    request: Request,
    search: Optional[str] = None,
    riskLevel: Optional[str] = None,
    dateFrom: Optional[str] = None,
    dateTo: Optional[str] = None,
    providerId: Optional[str] = None,
    procedureCode: Optional[str] = None,
    fraudType: Optional[str] = None,
    status: Optional[str] = None,
    minFraudScore: Optional[float] = None,
    maxFraudScore: Optional[float] = None,
    page: int = 1,
    pageSize: int = Query(25, le=100),
    sortBy: str = "fraudScore",
    sortDir: str = "desc",
    db: Session = Depends(get_db),
):
    data = claim_service.list_claims(
        db,
        search=search,
        risk_level=riskLevel,
        date_from=dateFrom,
        date_to=dateTo,
        provider_id=providerId,
        procedure_code=procedureCode,
        fraud_type=fraudType,
        status=status,
        min_fraud_score=minFraudScore,
        max_fraud_score=maxFraudScore,
        page=page,
        page_size=pageSize,
        sort_by=sortBy,
        sort_dir=sortDir,
    )
    return make_response(data, request.state.request_id)


@router.post("/retrain")
@router.post("/sync-retrain")
def retrain(background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    data = retraining_service.start_sync_retrain(request, db)
    task = data.pop("backgroundTask", None)
    if task:
        background_tasks.add_task(task)
    return make_response(data, request.state.request_id)


@router.get("/retrain/latest")
@router.get("/sync-retrain/latest")
def latest_retrain(request: Request, db: Session = Depends(get_db)):
    data = retraining_service.latest_sync_retrain(db)
    return make_response({"run": data}, request.state.request_id)


@router.get("/{claim_id}")
def get_claim(claim_id: str, request: Request, db: Session = Depends(get_db)):
    data = claim_service.get_claim_analysis(db, claim_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Claim with ID {claim_id} was not found.")
    return make_response(data, request.state.request_id)


@router.post("/{claim_id}/flag-siu")
def flag_siu(claim_id: str, request: Request, db: Session = Depends(get_db)):
    data = claim_service.flag_claim(db, claim_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Claim with ID {claim_id} was not found.")
    return make_response(data, request.state.request_id)


@router.get("/{claim_id}/report")
def claim_report(claim_id: str, request: Request):
    return make_response(claim_service.report_payload(claim_id), request.state.request_id)

