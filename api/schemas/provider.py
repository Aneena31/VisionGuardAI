from __future__ import annotations

from pydantic import BaseModel


class ProviderSummary(BaseModel):
    id: str
    name: str
    specialty: str
    riskScore: float
    claimCount: int
    highRiskRatio: float
    totalAllowedAmount: float
    city: str
    state: str


class ProviderDetail(BaseModel):
    provider: ProviderSummary
    procedurePeerComparison: list[dict]
    aiSummary: dict

