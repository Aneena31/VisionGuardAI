from __future__ import annotations

from pydantic import BaseModel


class KpiMetric(BaseModel):
    value: float | int
    trendPercent: float | None = None
    trendDirection: str | None = None
    shareOfTotalPercent: float | None = None


class DashboardOverview(BaseModel):
    kpis: dict
    fraudTrend: list[dict]
    riskDistribution: dict
    topSuspiciousProviders: list[dict]

