from __future__ import annotations

from math import ceil

from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session

from db.models import Claim, ProviderGold


def list_providers(
    db: Session,
    search: str | None = None,
    risk_level: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "riskScore",
    sort_dir: str = "desc",
) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    query = db.query(ProviderGold)
    if search:
        term = f"%{search}%"
        query = query.filter(or_(ProviderGold.id.ilike(term), ProviderGold.name.ilike(term), ProviderGold.specialty.ilike(term)))
    if risk_level:
        query = query.filter(ProviderGold.provider_risk_level == risk_level)
    total = query.count()
    column = _provider_sort_column(sort_by)
    query = query.order_by(desc(column) if sort_dir != "asc" else asc(column))
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [provider_summary(provider) for provider in items],
        "pagination": {"page": page, "pageSize": page_size, "totalItems": total, "totalPages": ceil(total / page_size)},
    }


def get_provider_detail(db: Session, provider_id: str) -> dict | None:
    provider = db.get(ProviderGold, provider_id)
    if not provider:
        return None
    return {
        "provider": provider_summary(provider),
        "procedurePeerComparison": procedure_peer_comparison(db, provider_id),
        "aiSummary": {
            "patternDeviation": provider.ai_pattern_deviation or "",
            "velocityIndicator": provider.ai_velocity_indicator or "",
            "recommendation": provider.ai_recommendation or "",
        },
    }


def procedure_peer_comparison(db: Session, provider_id: str) -> list[dict]:
    provider_counts = (
        db.query(Claim.procedure_code, func.count(Claim.id).label("provider_volume"))
        .filter(Claim.provider_id == provider_id)
        .group_by(Claim.procedure_code)
        .all()
    )
    result = []
    for procedure_code, provider_volume in provider_counts[:10]:
        peer_subquery = (
            db.query(Claim.provider_id.label("provider_id"), func.count(Claim.id).label("volume"))
            .filter(Claim.procedure_code == procedure_code)
            .group_by(Claim.provider_id)
            .subquery()
        )
        peer_average = db.query(func.avg(peer_subquery.c.volume)).scalar() or 0
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


def _provider_sort_column(sort_by: str):
    return {
        "riskScore": ProviderGold.provider_risk_score,
        "claimCount": ProviderGold.total_claims,
        "totalAllowedAmount": ProviderGold.total_allowed,
        "name": ProviderGold.name,
    }.get(sort_by, ProviderGold.provider_risk_score)
