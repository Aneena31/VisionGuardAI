from __future__ import annotations

from math import ceil
from typing import Optional

from sqlalchemy.orm import Session

from api.services.historical_data_service import get_historical_data
from db.models import Claim, ProviderGold

def list_providers(
    db: Session,
    search: Optional[str] = None,
    risk_level: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "riskScore",
    sort_dir: str = "desc",
) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    providers = [
        provider
        for provider in get_historical_data().providers_by_id.values()
        if _matches_provider(provider, search, risk_level)
    ]
    total = len(providers)
    providers.sort(key=lambda provider: _provider_sort_value(provider, sort_by), reverse=sort_dir != "asc")
    items = providers[(page - 1) * page_size : page * page_size]
    return {
        "items": [provider_summary(provider) for provider in items],
        "pagination": {"page": page, "pageSize": page_size, "totalItems": total, "totalPages": ceil(total / page_size)},
    }


def get_provider_detail(db: Session, provider_id: str) -> Optional[dict]:
    data = get_historical_data()
    provider = data.providers_by_id.get(provider_id)
    if not provider:
        return None
    return {
        "provider": provider_summary(provider),
        "procedurePeerComparison": procedure_peer_comparison_from_claims(data.claims, provider_id),
        "aiSummary": {
            "patternDeviation": provider.ai_pattern_deviation or "",
            "velocityIndicator": provider.ai_velocity_indicator or "",
            "recommendation": provider.ai_recommendation or "",
        },
    }


def procedure_peer_comparison_from_claims(claims: list[Claim], provider_id: str) -> list[dict]:
    procedure_counts: dict[str, int] = {}
    peer_counts: dict[str, dict[str, int]] = {}
    for claim in claims:
        procedure_code = claim.procedure_code or ""
        if not procedure_code:
            continue
        peer_counts.setdefault(procedure_code, {})
        peer_counts[procedure_code][claim.provider_id] = peer_counts[procedure_code].get(claim.provider_id, 0) + 1
        if claim.provider_id == provider_id:
            procedure_counts[procedure_code] = procedure_counts.get(procedure_code, 0) + 1

    result = []
    for procedure_code, provider_volume in list(procedure_counts.items())[:10]:
        peer_volumes = list(peer_counts.get(procedure_code, {}).values())
        peer_average = sum(peer_volumes) / len(peer_volumes) if peer_volumes else 0
        result.append(
            {
                "procedureCode": procedure_code,
                "providerVolume": int(provider_volume or 0),
                "peerAverageVolume": float(peer_average),
            }
        )
    return result


def provider_summary(provider: ProviderGold) -> dict:
    return {
        "id": provider.id,
        "name": provider.name or provider.id,
        "specialty": provider.specialty or "",
        "riskScore": round(provider.provider_risk_score or 0, 1),
        "claimCount": provider.total_claims or 0,
        "highRiskRatio": provider.high_risk_ratio or 0,
        "totalAllowedAmount": provider.total_allowed or 0,
        "city": provider.city or "",
        "state": provider.state or "",
    }


def _matches_provider(provider: ProviderGold, search: Optional[str], risk_level: Optional[str]) -> bool:
    if search:
        term = search.lower()
        haystack = " ".join([provider.id or "", provider.name or "", provider.specialty or ""]).lower()
        if term not in haystack:
            return False
    if risk_level and provider.provider_risk_level != risk_level:
        return False
    return True


def _provider_sort_value(provider: ProviderGold, sort_by: str):
    if sort_by == "claimCount":
        return provider.total_claims or 0
    if sort_by == "totalAllowedAmount":
        return provider.total_allowed or 0
    if sort_by == "name":
        return provider.name or provider.id or ""
    return provider.provider_risk_score or 0
