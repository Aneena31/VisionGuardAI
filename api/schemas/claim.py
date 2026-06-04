from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class ClaimSummary(BaseModel):
    id: str
    providerId: str
    providerName: Optional[str] = None
    memberId: Optional[str] = None
    procedureCode: Optional[str] = None
    procedureDesc: Optional[str] = None
    allowedAmount: float
    fraudScore: float
    riskLevel: str
    fraudType: Optional[str] = None
    clusterId: Optional[str] = None
    date: Optional[str] = None
    status: str


class PipelineOutput(BaseModel):
    runId: str
    status: str
    submittedAt: Optional[str] = None
    completedAt: Optional[str] = None
    statusText: str


class ClaimAnalysis(BaseModel):
    claim: dict[str, Any]
    analysis: dict[str, Any]

