from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


def _num(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    return str(value)


def _service_month(value: Any) -> Any:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return pd.Timestamp(date.today().replace(day=1))
    return parsed


def load_and_clean(file_path: str) -> pd.DataFrame:
    """Load raw Excel, derive standard pipeline columns, and assign row_id."""
    df = pd.read_excel(file_path)
    df = df.copy()

    df["AmtAllowed"] = pd.to_numeric(df.get("AllowedAmount"), errors="coerce").fillna(0)
    df["Units"] = pd.to_numeric(df.get("UnitsUsed"), errors="coerce").fillna(0)
    df["PatientAge"] = pd.to_numeric(df.get("MemberAge"), errors="coerce").fillna(0)
    df["AmtCharged"] = pd.to_numeric(df.get("AmtCharged"), errors="coerce").fillna(0)
    df["ProviderId"] = df.get("ProviderId", "").astype(str)
    df["ProcedureCode"] = df.get("ProcedureCode", "").astype(str)
    df["ServiceCategoryName"] = df.get("ServiceCategoryName", "").fillna("").astype(str)
    df["BenefitCategoryName"] = df.get("BenefitCategoryName", "").fillna("").astype(str)
    df["BenefitType"] = df.get("BenefitType", "Other").fillna("Other").astype(str)
    df["ServiceMonth"] = pd.to_datetime(df.get("ServiceMonth"), errors="coerce")

    denominator = df["AmtAllowed"].replace(0, np.nan)
    df["BilledAmountToAllowedRatio"] = (df["AmtCharged"] / denominator).replace([np.inf, -np.inf], np.nan).fillna(0)
    df["row_id"] = df.index + 1
    return df


def clean_single(claim_dict: dict) -> dict:
    """Normalize a single claim dict for real-time scoring."""
    claim = claim_dict.copy()
    claim["AmtAllowed"] = _num(claim.get("allowedAmount", claim.get("AmtAllowed", claim.get("AllowedAmount", 0))))
    claim["Units"] = _num(claim.get("units", claim.get("Units", claim.get("UnitsUsed", 1))), default=1)
    claim["PatientAge"] = int(_num(claim.get("memberAge", claim.get("PatientAge", claim.get("MemberAge", 0)))))
    claim["AmtCharged"] = _num(claim.get("amtCharged", claim.get("AmtCharged", 0)))
    allowed = claim["AmtAllowed"]
    claim["BilledAmountToAllowedRatio"] = claim["AmtCharged"] / allowed if allowed else 0
    claim["row_id"] = int(claim.get("row_id", 0) or 0)
    claim["ProcedureCode"] = _text(claim.get("procedureCode", claim.get("ProcedureCode", ""))).upper()
    claim["ProcedureDesc"] = _text(claim.get("procedureDesc", claim.get("ProcedureDesc", "")))
    claim["ProviderId"] = _text(claim.get("providerId", claim.get("ProviderId", "")))
    claim["MemberId"] = _text(claim.get("memberId", claim.get("MemberId", "")))
    claim["MemberAge"] = claim["PatientAge"]
    claim["MemberGender"] = _text(claim.get("memberGender", claim.get("MemberGender", "")))
    claim["BenefitType"] = _text(claim.get("benefitType", claim.get("BenefitType", "Other")), "Other")
    claim["ServiceCategoryName"] = _text(claim.get("serviceCategoryName", claim.get("ServiceCategoryName", "")))
    claim["BenefitCategoryName"] = _text(claim.get("benefitCategoryName", claim.get("BenefitCategoryName", "")))
    claim["ServiceMonth"] = _service_month(claim.get("serviceDate", claim.get("ServiceMonth")))
    return claim

