from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler


FEATURE_SOURCES = [
    ("allowed_amount", ["AmtAllowed"]),
    ("units", ["Units"]),
    ("billed_ratio", ["BilledAmountToAllowedRatio"]),
    ("member_age", ["PatientAge", "MemberAge"]),
    ("rule_score", ["Rule_Score_Norm", "Rule_Score_Total"]),
    ("claim_history_score", ["Claim_Stat_Score_Norm", "Claim_Stat_Score"]),
    ("provider_history_score", ["Provider_Stat_Score_Norm", "Provider_Stat_Score"]),
    ("pattern_score", ["ML_Anomaly_Score_Norm", "ML_Anomaly_Score"]),
    ("final_score", ["Final_Combined_Score"]),
]


def compute_similarity(df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """Attach nearest historical claim IDs using processed claim features."""
    out = df.copy()
    if len(out) <= 1:
        out["Similar_Claim_Ids"] = json.dumps([])
        return out

    features = _feature_matrix(out)
    scaled = StandardScaler().fit_transform(features)
    neighbor_count = min(top_n + 1, len(out))
    neighbors = NearestNeighbors(n_neighbors=neighbor_count, metric="euclidean")
    neighbors.fit(scaled)
    _, indices = neighbors.kneighbors(scaled)

    similar_ids = []
    for row_index, row_neighbors in enumerate(indices):
        ids = []
        for neighbor_index in row_neighbors:
            if int(neighbor_index) == row_index:
                continue
            ids.append(_claim_id(out.iloc[int(neighbor_index)]))
            if len(ids) >= top_n:
                break
        similar_ids.append(json.dumps(ids))

    out["Similar_Claim_Ids"] = similar_ids
    return out


def find_closest_claim(claim: dict[str, Any], historical_df: pd.DataFrame | None) -> dict[str, Any] | None:
    """Find the closest processed historical claim for a newly scored claim."""
    if historical_df is None or historical_df.empty:
        return None

    candidates = _candidate_pool(claim, historical_df)
    if candidates.empty:
        return None

    features = _feature_matrix(candidates)
    query = _feature_matrix(pd.DataFrame([claim]))
    scaler = StandardScaler()
    scaled_candidates = scaler.fit_transform(features)
    scaled_query = scaler.transform(query)

    neighbors = NearestNeighbors(n_neighbors=1, metric="euclidean")
    neighbors.fit(scaled_candidates)
    distances, indices = neighbors.kneighbors(scaled_query)

    distance = float(distances[0][0])
    row = candidates.iloc[int(indices[0][0])]
    return _similar_claim_payload(row, claim, distance)


def _candidate_pool(claim: dict[str, Any], historical_df: pd.DataFrame) -> pd.DataFrame:
    procedure = str(claim.get("ProcedureCode", "") or "").upper()
    cluster = str(claim.get("cluster_id", "") or "")
    benefit_type = str(claim.get("BenefitType", "") or "").upper()

    procedure_values = _text_column(historical_df, "ProcedureCode")
    procedure_matches = historical_df[procedure_values.str.upper() == procedure]
    if procedure and not procedure_matches.empty:
        return procedure_matches.copy()

    if cluster and cluster != "CL-00" and "cluster_id" in historical_df.columns:
        cluster_matches = historical_df[historical_df["cluster_id"].fillna("").astype(str) == cluster]
        if not cluster_matches.empty:
            return cluster_matches.copy()

    if benefit_type and "BenefitType" in historical_df.columns:
        benefit_matches = historical_df[historical_df["BenefitType"].fillna("").astype(str).str.upper() == benefit_type]
        if not benefit_matches.empty:
            return benefit_matches.copy()

    return historical_df.copy()


def _text_column(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([""] * len(df), index=df.index, dtype=str)
    return df[column].fillna("").astype(str)


def _feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    columns = {}
    for feature_name, source_names in FEATURE_SOURCES:
        columns[feature_name] = _first_numeric(df, source_names)
    return pd.DataFrame(columns).replace([np.inf, -np.inf], 0).fillna(0)


def _first_numeric(df: pd.DataFrame, source_names: list[str]) -> pd.Series:
    for source_name in source_names:
        if source_name in df.columns:
            return pd.to_numeric(df[source_name], errors="coerce").fillna(0)
    return pd.Series(np.zeros(len(df)), index=df.index)


def _similar_claim_payload(row: pd.Series, claim: dict[str, Any], distance: float) -> dict[str, Any]:
    similarity_score = float(np.clip(100 * np.exp(-distance / 3), 0, 100))
    return {
        "id": _claim_id(row),
        "providerId": _provider_id(row),
        "providerName": _text(row.get("ProviderName", row.get("provider_name", ""))) or _provider_id(row),
        "procedureCode": _text(row.get("ProcedureCode")),
        "procedureDesc": _text(row.get("ProcedureDesc", row.get("procedure_desc", ""))),
        "allowedAmount": round(_float(row.get("AmtAllowed")), 2),
        "billedAmount": round(_float(row.get("AmtCharged")), 2),
        "billedToAllowedRatio": round(_float(row.get("BilledAmountToAllowedRatio")), 2),
        "fraudScore": round(_float(row.get("Final_Combined_Score")), 1),
        "riskLevel": _text(row.get("Final_Risk_Level")) or "Low",
        "issueType": _text(row.get("Final_Fraud_Type")) or "No significant issue",
        "clusterId": _text(row.get("cluster_id", row.get("ClusterId", "CL-00"))) or "CL-00",
        "date": _date_text(row.get("ServiceMonth", row.get("service_date", ""))),
        "status": _text(row.get("status", row.get("Status", ""))) or "Pending",
        "similarityScore": round(similarity_score, 1),
        "matchReason": _match_reason(row, claim),
    }


def _match_reason(row: pd.Series, claim: dict[str, Any]) -> str:
    reasons = []
    if _same_text(row.get("ProcedureCode"), claim.get("ProcedureCode")):
        reasons.append("same procedure code")
    if _same_text(_provider_id(row), claim.get("ProviderId")):
        reasons.append("same provider")
    if _same_text(row.get("Final_Fraud_Type"), claim.get("Final_Fraud_Type")):
        reasons.append("same likely issue type")
    if _close_amount(row.get("AmtAllowed"), claim.get("AmtAllowed"), tolerance=0.25):
        reasons.append("similar allowed amount")
    if _close_amount(row.get("BilledAmountToAllowedRatio"), claim.get("BilledAmountToAllowedRatio"), tolerance=0.35):
        reasons.append("similar billed-to-allowed relationship")
    if reasons:
        return ", ".join(reasons[:3])
    return "closest overall profile across amount, units, billing relationship, and review scores"


def _claim_id(row: pd.Series) -> str:
    existing_id = _text(row.get("ClaimRecordId", row.get("id", "")))
    if existing_id:
        return existing_id
    raw_id = _text(row.get("ClaimId", row.get("ClaimID", row.get("claim_id", ""))))
    if raw_id:
        try:
            raw_id = str(int(float(raw_id)))
        except ValueError:
            pass
        return raw_id if raw_id.startswith("CLM-") else f"CLM-{raw_id}"
    row_id = _text(row.get("row_id", ""))
    return f"CLM-{row_id}" if row_id else "CLM-UNKNOWN"


def _provider_id(row: pd.Series) -> str:
    raw = _text(row.get("ProviderId", row.get("provider_id", ""))).strip()
    if not raw:
        return ""
    return raw if raw.startswith("PRV-") else f"PRV-{raw[-7:]}"


def _same_text(left: Any, right: Any) -> bool:
    return _text(left).upper() == _text(right).upper() and bool(_text(left))


def _close_amount(left: Any, right: Any, tolerance: float) -> bool:
    left_value = _float(left)
    right_value = _float(right)
    if left_value == 0 and right_value == 0:
        return True
    denominator = max(abs(left_value), abs(right_value), 1)
    return abs(left_value - right_value) / denominator <= tolerance


def _date_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return _text(value) or None
    return parsed.date().isoformat()


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)


def _float(value: Any) -> float:
    try:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
