from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel


class KpiMetric(BaseModel):
<<<<<<< HEAD
    value: float | int
=======
    value: Union[float, int]
>>>>>>> dev
    trendPercent: Optional[float] = None
    trendDirection: Optional[str] = None
    shareOfTotalPercent: Optional[float] = None


class DashboardOverview(BaseModel):
    kpis: dict
    fraudTrend: list[dict]
    riskDistribution: dict
    topSuspiciousProviders: list[dict]

