from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from api.services import historical_data_service
from api.services.provider_service import provider_summary


def overview(db: Session) -> dict:
    data = historical_data_service.get_historical_data()
    claims = data.claims
    providers = list(data.providers_by_id.values())

    total_claims = len(claims)
    total_allowed = sum(float(claim.amt_allowed or 0) for claim in claims)
    avg_score = (
        sum(float(claim.final_combined_score or 0) for claim in claims) / total_claims
        if total_claims
        else 0
    )
    critical = sum(1 for claim in claims if claim.final_risk_level == "Critical")

    trend = defaultdict(lambda: {"fraudAmount": 0.0, "claimCount": 0})
    risk_counts = Counter()
    for claim in claims:
        service_date = claim.service_date
        risk_level = claim.final_risk_level or "Low"
        amt_allowed = claim.amt_allowed or 0
        risk_counts[risk_level or "Low"] += 1
        if service_date:
            key = service_date.strftime("%Y-%m")
            trend[key]["claimCount"] += 1
            if risk_level in ["High", "Critical"]:
                trend[key]["fraudAmount"] += float(amt_allowed or 0)

    top_providers = sorted(providers, key=lambda provider: provider.provider_risk_score or 0, reverse=True)[:5]
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
