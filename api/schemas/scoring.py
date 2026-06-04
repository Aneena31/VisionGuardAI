from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


SourceType = Literal["x12_837", "csv", "json", "manual"]


class ClaimInput(BaseModel):
    procedureCode: str
    procedureDesc: Optional[str] = ""
    allowedAmount: float
    amtCharged: float = 0
    units: float = 1
    memberAge: int = 0
    memberGender: Optional[str] = None
    providerId: str
    serviceDate: Optional[str] = None
    benefitType: Optional[str] = "Other"
    serviceCategoryName: Optional[str] = ""
    benefitCategoryName: Optional[str] = ""


class ScoringJobCreate(BaseModel):
    sourceType: SourceType = "manual"
    claim: ClaimInput


class ScoringJobResponse(BaseModel):
    jobId: str
    status: str
    sourceType: str
    submittedAt: str


class JobStage(BaseModel):
    code: str
    label: str
    status: str
    progressPercent: int


class JobStatus(BaseModel):
    jobId: str
    status: str
    progressPercent: int
    activeStage: Optional[str] = None
    stages: list[JobStage]
