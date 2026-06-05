from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.schemas.common import make_response
from db.database import get_db
from db.models import Claim, ProviderGold


router = APIRouter(prefix="/visionguard/search", tags=["search"])


@router.get("")
def search(query: str, request: Request, db: Session = Depends(get_db)):
    term = f"%{query}%"
    claims = (
        db.query(Claim)
        .filter(or_(Claim.id.ilike(term), Claim.provider_id.ilike(term), Claim.procedure_code.ilike(term)))
        .limit(5)
        .all()
    )
    providers = (
        db.query(ProviderGold)
        .filter(or_(ProviderGold.id.ilike(term), ProviderGold.name.ilike(term)))
        .limit(5)
        .all()
    )
    return make_response(
        {
            "claims": [
                {"id": claim.id, "providerName": claim.provider_name or claim.provider_id, "riskLevel": claim.final_risk_level}
                for claim in claims
            ],
            "providers": [
                {"id": provider.id, "name": provider.name or provider.id, "riskScore": provider.provider_risk_score or 0}
                for provider in providers
            ],
        },
        request.state.request_id,
    )

