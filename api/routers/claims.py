from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from api.services import claim_service
from db.database import get_db


router = APIRouter(prefix="/api/claims", tags=["claims"])


@router.get("")
def list_claims(
    request: Request,
    search: str | None = None,
    riskLevel: str | None = None,
    dateFrom: str | None = None,
    dateTo: str | None = None,
    providerId: str | None = None,
    procedureCode: str | None = None,
    fraudType: str | None = None,
    status: str | None = None,
    minFraudScore: float | None = None,
    maxFraudScore: float | None = None,
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

