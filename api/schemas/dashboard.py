from __future__ import annotations

from pydantic import BaseModel


class KpiMetric(BaseModel):
    value: float | int
    trendPercent: Optional[float] = None
    trendDirection: Optional[str] = None
    shareOfTotalPercent: Optional[float] = None


class DashboardOverview(BaseModel):
    kpis: dict
    fraudTrend: list[dict]
    riskDistribution: dict
    topSuspiciousProviders: list[dict]

