from __future__ import annotations

from fastapi import APIRouter, Request

from api.schemas.common import make_response
from api.services.historical_data_service import get_historical_data


router = APIRouter(prefix="/visionguard/search", tags=["search"])


@router.get("")
def search(query: str, request: Request):
    data = get_historical_data()
    term = query.lower()
    claims = [
        claim
        for claim in data.claims
        if term in " ".join([claim.id or "", claim.provider_id or "", claim.procedure_code or ""]).lower()
    ][:5]
    providers = [
        provider
        for provider in data.providers_by_id.values()
        if term in " ".join([provider.id or "", provider.name or ""]).lower()
    ][:5]
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
