from __future__ import annotations

from datetime import date
from pathlib import Path
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


SUPPORTED_DATA_EXTENSIONS = {".csv", ".xls", ".xlsx"}


def load_and_clean(file_path: str) -> pd.DataFrame:
    """Load one raw claims file, derive standard pipeline columns, and assign row_id."""
    df = _read_claim_file(Path(file_path))
    return _normalize_claims(df)


def load_and_clean_source(source: str) -> pd.DataFrame:
    """Load one claims file or every supported claims file in a directory."""
    path = Path(source)
    if path.is_dir():
        files = sorted(
            item
            for item in path.iterdir()
            if item.is_file()
            and item.suffix.lower() in SUPPORTED_DATA_EXTENSIONS
            and not item.name.startswith("~$")
        )
        if not files:
            supported = ", ".join(sorted(SUPPORTED_DATA_EXTENSIONS))
            raise FileNotFoundError(f"No supported claims files ({supported}) found in: {path}")
        frames = [_normalize_claims(_read_claim_file(file)) for file in files]
        combined = pd.concat(frames, ignore_index=True)
        combined["row_id"] = combined.index + 1
        return combined
    return load_and_clean(str(path))


def _read_claim_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path)
    supported = ", ".join(sorted(SUPPORTED_DATA_EXTENSIONS))
    raise ValueError(f"Unsupported claims file type '{suffix}'. Supported types: {supported}")


def _normalize_claims(df: pd.DataFrame) -> pd.DataFrame:
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
