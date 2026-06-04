from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ClaimSummary(BaseModel):
    id: str
    providerId: str
    providerName: str | None = None
    memberId: str | None = None
    procedureCode: str | None = None
    procedureDesc: str | None = None
    allowedAmount: float
    fraudScore: float
    riskLevel: str
    fraudType: str | None = None
    clusterId: str | None = None
    date: str | None = None
    status: str


class PipelineOutput(BaseModel):
    runId: str
    status: str
    submittedAt: str | None = None
    completedAt: str | None = None
    statusText: str


class ClaimAnalysis(BaseModel):
    claim: dict[str, Any]
    analysis: dict[str, Any]

