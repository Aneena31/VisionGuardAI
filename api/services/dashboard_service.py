from __future__ import annotations

import time
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from api.services.historical_data_service import get_historical_data
from api.services.provider_service import provider_summary


def overview(db: Session) -> dict:
    t0 = time.perf_counter()
    print("[VisionGuard] dashboard overview started", flush=True)

    data = get_historical_data()
    claims = data.claims
    providers = list(data.providers_by_id.values())
    total_claims = len(claims)
    total_allowed = sum(claim.amt_allowed or 0 for claim in claims)
    avg_score = sum(claim.final_combined_score or 0 for claim in claims) / total_claims if total_claims else 0
    critical = sum(1 for claim in claims if claim.final_risk_level == "Critical")
    risk_counts = Counter(claim.final_risk_level or "Low" for claim in claims)
    trend_counts: dict[str, dict[str, float]] = defaultdict(lambda: {"claim_count": 0, "fraud_amount": 0.0})
    for claim in claims:
        if not claim.service_date:
            continue
        period = claim.service_date.strftime("%Y-%m")
        trend_counts[period]["claim_count"] += 1
        if claim.final_risk_level in ["High", "Critical"]:
            trend_counts[period]["fraud_amount"] += claim.amt_allowed or 0
    top_providers = sorted(providers, key=lambda provider: provider.provider_risk_score or 0, reverse=True)[:5]
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
                "period": period,
                "label": _month_label(period),
                "fraudAmount": float(values["fraud_amount"] or 0),
                "claimCount": int(values["claim_count"] or 0),
            }
            for period, values in sorted(trend_counts.items())
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
