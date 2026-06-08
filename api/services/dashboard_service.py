from __future__ import annotations

import time

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from api.services.provider_service import provider_summary
from db.models import Claim, ProviderGold


def overview(db: Session) -> dict:
    t0 = time.perf_counter()
    print("[VisionGuard] dashboard overview started", flush=True)

    total_claims = db.query(func.count(Claim.id)).scalar() or 0
    total_allowed = db.query(func.coalesce(func.sum(Claim.amt_allowed), 0)).scalar() or 0
    avg_score = db.query(func.coalesce(func.avg(Claim.final_combined_score), 0)).scalar() or 0
    critical = db.query(func.count(Claim.id)).filter(Claim.final_risk_level == "Critical").scalar() or 0

    trend_rows = (
        db.query(
            func.strftime("%Y-%m", Claim.service_date).label("period"),
            func.count(Claim.id).label("claim_count"),
            func.coalesce(
                func.sum(
                    case(
                        (Claim.final_risk_level.in_(["High", "Critical"]), Claim.amt_allowed),
                        else_=0,
                    )
                ),
                0,
            ).label("fraud_amount"),
        )
        .filter(Claim.service_date.isnot(None))
        .group_by("period")
        .order_by("period")
        .all()
    )
    risk_rows = (
        db.query(Claim.final_risk_level, func.count(Claim.id))
        .group_by(Claim.final_risk_level)
        .all()
    )
    risk_counts = {(level or "Low"): count for level, count in risk_rows}

    top_providers = (
        db.query(ProviderGold)
        .order_by(ProviderGold.provider_risk_score.desc())
        .limit(5)
        .all()
    )
    payload = {
        "kpis": {
            "totalClaimsAnalyzed": {"value": total_claims, "trendPercent": 0.0, "trendDirection": "up"},
            "totalAllowedAmount": {"value": float(total_allowed), "trendPercent": 0.0, "trendDirection": "up"},
            "averageFraudScore": {"value": float(avg_score), "trendPercent": 0.0, "trendDirection": "up"},
            "criticalClaimsFlagged": {
                "value": critical,
                "shareOfTotalPercent": (critical / total_claims * 100) if total_claims else 0,
            },
        },
        "fraudTrend": [
            {
                "period": row.period,
                "label": _month_label(row.period),
                "fraudAmount": float(row.fraud_amount or 0),
                "claimCount": int(row.claim_count or 0),
            }
            for row in trend_rows
        ],
        "riskDistribution": {
            "totalAnalyzed": total_claims,
            "items": [{"riskLevel": level, "count": risk_counts.get(level, 0)} for level in ["Low", "Medium", "High", "Critical"]],
        },
        "topSuspiciousProviders": [provider_summary(provider) for provider in top_providers],
    }
    print(
        f"[VisionGuard] dashboard overview completed claims={total_claims:,} providers={len(top_providers)} "
        f"duration={time.perf_counter() - t0:.3f}s",
        flush=True,
    )
    return payload


def export_dashboard() -> dict:
    return {"exportId": "EXP-POC-001", "status": "queued", "format": "pdf"}


def _month_label(period: str) -> str:
    month = int(period.split("-")[1])
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return labels[month - 1]
