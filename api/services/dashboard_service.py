from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Claim, ProviderGold
from api.services.provider_service import provider_summary


def overview(db: Session) -> dict:
    total_claims = db.query(func.count(Claim.id)).scalar() or 0
    total_allowed = db.query(func.coalesce(func.sum(Claim.amt_allowed), 0)).scalar() or 0
    avg_score = db.query(func.coalesce(func.avg(Claim.final_combined_score), 0)).scalar() or 0
    critical = db.query(func.count(Claim.id)).filter(Claim.final_risk_level == "Critical").scalar() or 0

    claims = db.query(Claim.service_date, Claim.final_risk_level, Claim.amt_allowed).all()
    trend = defaultdict(lambda: {"fraudAmount": 0.0, "claimCount": 0})
    risk_counts = Counter()
    for service_date, risk_level, amt_allowed in claims:
        risk_counts[risk_level or "Low"] += 1
        if service_date:
            key = service_date.strftime("%Y-%m")
            trend[key]["claimCount"] += 1
            if risk_level in ["High", "Critical"]:
                trend[key]["fraudAmount"] += float(amt_allowed or 0)

    top_providers = (
        db.query(ProviderGold).order_by(ProviderGold.provider_risk_score.desc()).limit(5).all()
    )
    return {
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
            {"period": period, "label": _month_label(period), **values}
            for period, values in sorted(trend.items())
        ],
        "riskDistribution": {
            "totalAnalyzed": total_claims,
            "items": [{"riskLevel": level, "count": risk_counts.get(level, 0)} for level in ["Low", "Medium", "High", "Critical"]],
        },
        "topSuspiciousProviders": [provider_summary(provider) for provider in top_providers],
    }


def export_dashboard() -> dict:
    return {"exportId": "EXP-POC-001", "status": "queued", "format": "pdf"}


def _month_label(period: str) -> str:
    month = int(period.split("-")[1])
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return labels[month - 1]

