from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline import config


def apply_final_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """Compute weighted final composite score and fraud labels."""
    out = df.copy()
    out["Rule_Score_Norm"] = (100 * out["Rule_Score_Total"] / config.MAX_RULE_SCORE).clip(0, 100)
    out["Claim_Stat_Score_Norm"] = out["Claim_Stat_Score"].clip(0, 100)
    out["Provider_Stat_Score_Norm"] = out["Provider_Stat_Score"].clip(0, 100)
    out["ML_Anomaly_Score_Norm"] = out["ML_Anomaly_Score"].clip(0, 100)
    out["Final_Combined_Score"] = (
        out["Rule_Score_Norm"] * config.WEIGHT_RULE
        + out["Claim_Stat_Score_Norm"] * config.WEIGHT_CLAIM_STAT
        + out["Provider_Stat_Score_Norm"] * config.WEIGHT_PROV_STAT
        + out["ML_Anomaly_Score_Norm"] * config.WEIGHT_ML
    ).clip(0, 100)
    out["Final_Risk_Level"] = out["Final_Combined_Score"].apply(risk_level)
    out["Final_Fraud_Type"] = out.apply(fraud_type, axis=1)
    out["Final_Fraud_Reason"] = out.apply(final_reason, axis=1)
    out["Final_Narrative"] = out.apply(
        lambda row: f"{row['Final_Risk_Level']} risk claim scored {row['Final_Combined_Score']:.1f}/100. {row['Final_Fraud_Reason']}",
        axis=1,
    )
    out["cluster_id"] = out["Final_Fraud_Type"].apply(assign_cluster)
    return out


def apply_final_scoring_single(scores_dict: dict) -> dict:
    """Single-claim final scoring."""
    claim = scores_dict.copy()
    claim["Rule_Score_Norm"] = float(np.clip(100 * claim.get("Rule_Score_Total", 0) / config.MAX_RULE_SCORE, 0, 100))
    claim["Claim_Stat_Score_Norm"] = float(np.clip(claim.get("Claim_Stat_Score", 0), 0, 100))
    claim["Provider_Stat_Score_Norm"] = float(np.clip(claim.get("Provider_Stat_Score", 0), 0, 100))
    claim["ML_Anomaly_Score_Norm"] = float(np.clip(claim.get("ML_Anomaly_Score", 0), 0, 100))
    final_score = (
        claim["Rule_Score_Norm"] * config.WEIGHT_RULE
        + claim["Claim_Stat_Score_Norm"] * config.WEIGHT_CLAIM_STAT
        + claim["Provider_Stat_Score_Norm"] * config.WEIGHT_PROV_STAT
        + claim["ML_Anomaly_Score_Norm"] * config.WEIGHT_ML
    )
    claim["Final_Combined_Score"] = float(np.clip(final_score, 0, 100))
    claim["Final_Risk_Level"] = risk_level(claim["Final_Combined_Score"])
    claim["Final_Fraud_Type"] = fraud_type(claim)
    claim["Final_Fraud_Reason"] = final_reason(claim)
    claim["Final_Narrative"] = (
        f"{claim['Final_Risk_Level']} risk claim scored {claim['Final_Combined_Score']:.1f}/100. "
        f"{claim['Final_Fraud_Reason']}"
    )
    claim["cluster_id"] = assign_cluster(claim["Final_Fraud_Type"])
    return claim


def risk_level(score: float) -> str:
    if score >= config.RISK_CRITICAL:
        return "Critical"
    if score >= config.RISK_HIGH:
        return "High"
    if score >= config.RISK_MEDIUM:
        return "Medium"
    return "Low"


def fraud_type(row) -> str:
    getter = row.get if isinstance(row, dict) else row.get
    if float(getter("ML_Anomaly_Score_Norm", 0) or 0) > 75:
        return "ML Pattern Anomaly"
    if float(getter("Provider_Stat_Score_Norm", 0) or 0) > 75:
        return "Provider Outlier Behavior"
    if float(getter("Rule_Score_Norm", 0) or 0) > 75:
        return "Rule-Based Upcoding / High-Cost"
    if float(getter("Claim_Stat_Score_Norm", 0) or 0) > 75:
        return "Claim-Level Outlier"
    return "No Significant Fraud Indicators"


def final_reason(row) -> str:
    getter = row.get if isinstance(row, dict) else row.get
    fraud = getter("Final_Fraud_Type", None) or fraud_type(row)
    if fraud == "ML Pattern Anomaly":
        return getter("ML_Anomaly_Narrative", "ML behavior deviates from historical patterns.")
    if fraud == "Provider Outlier Behavior":
        return "Provider billing pattern deviates from peer providers."
    if fraud == "Rule-Based Upcoding / High-Cost":
        return getter("Rule_Narrative", "Deterministic rule engine found upcoding or high-cost signals.")
    if fraud == "Claim-Level Outlier":
        return getter("Stat_Narrative", "Claim-level statistics are outliers.")
    return "No significant fraud indicators exceeded configured thresholds."


def assign_cluster(fraud_type_value: str) -> str:
    if fraud_type_value == "Rule-Based Upcoding / High-Cost":
        return "CL-02"
    if fraud_type_value == "ML Pattern Anomaly":
        return "CL-01"
    if fraud_type_value == "Provider Outlier Behavior":
        return "CL-03"
    return "CL-00"

