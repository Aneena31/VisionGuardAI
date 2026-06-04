from __future__ import annotations

import hashlib

import pandas as pd

from pipeline import config
from pipeline.ai_summary import generate_for_provider
from pipeline.scoring import risk_level


PRACTICE_NAMES = [
    "ClearSight Associates",
    "NorthStar Vision Center",
    "Advanced Optical Group",
    "Premier Eye Health",
    "Horizon Family Vision",
    "Keystone Ophthalmology",
    "Metro Lens Clinic",
    "VistaCare Optometry",
]
SPECIALTIES = ["Optometry", "Ophthalmology", "Vision Therapy", "Retail Optical", "Pediatric Optometry"]
CITIES = [
    ("Chicago", "IL"),
    ("New York", "NY"),
    ("Las Vegas", "NV"),
    ("Phoenix", "AZ"),
    ("Atlanta", "GA"),
    ("Dallas", "TX"),
    ("Columbus", "OH"),
    ("Denver", "CO"),
]


def build_provider_gold(df: pd.DataFrame) -> pd.DataFrame:
    """Build provider-level gold table with deterministic synthetic metadata."""
    grouped = df.groupby("ProviderId", dropna=False)
    gold = grouped.agg(
        raw_provider_id=("ProviderId", "first"),
        total_claims=("row_id", "count"),
        total_allowed=("AmtAllowed", "sum"),
        avg_allowed=("AmtAllowed", "mean"),
        avg_units=("Units", "mean"),
        high_risk_claims=("Final_Risk_Level", lambda values: values.isin(["High", "Critical"]).sum()),
        avg_final_score=("Final_Combined_Score", "mean"),
        avg_rule_score=("Rule_Score_Norm", "mean"),
        avg_stat_score=("Claim_Stat_Score_Norm", "mean"),
        avg_prov_stat_score=("Provider_Stat_Score_Norm", "mean"),
        avg_ml_score=("ML_Anomaly_Score_Norm", "mean"),
    ).reset_index()
    gold["id"] = gold["ProviderId"].apply(format_provider_id)
    gold["high_risk_ratio"] = (gold["high_risk_claims"] / gold["total_claims"]).fillna(0)
    gold["provider_risk_score"] = (
        gold["high_risk_ratio"] * 100 * config.PROVIDER_WEIGHT_HIGH_RISK_RATIO
        + gold["avg_final_score"] * config.PROVIDER_WEIGHT_AVG_FINAL
        + gold["avg_ml_score"] * config.PROVIDER_WEIGHT_AVG_ML
        + gold["avg_prov_stat_score"] * config.PROVIDER_WEIGHT_AVG_PROV_STAT
    ).clip(0, 100)
    gold["provider_risk_level"] = gold["provider_risk_score"].apply(risk_level)
    gold["provider_narrative"] = gold.apply(
        lambda row: f"{row['provider_risk_level']} provider risk with {row['high_risk_ratio']:.1%} high-risk claim ratio.",
        axis=1,
    )
    metadata = gold["ProviderId"].apply(_provider_metadata)
    gold["name"] = metadata.apply(lambda item: item["name"])
    gold["specialty"] = metadata.apply(lambda item: item["specialty"])
    gold["city"] = metadata.apply(lambda item: item["city"])
    gold["state"] = metadata.apply(lambda item: item["state"])
    provider_summaries = gold.apply(_provider_ai_summary, axis=1)
    gold["ai_pattern_deviation"] = provider_summaries.apply(lambda item: item["patternDeviation"])
    gold["ai_velocity_indicator"] = provider_summaries.apply(lambda item: item["velocityIndicator"])
    gold["ai_recommendation"] = provider_summaries.apply(lambda item: item["recommendation"])
    return gold[
        [
            "id",
            "raw_provider_id",
            "name",
            "specialty",
            "city",
            "state",
            "total_claims",
            "total_allowed",
            "avg_allowed",
            "avg_units",
            "high_risk_claims",
            "high_risk_ratio",
            "avg_final_score",
            "avg_rule_score",
            "avg_stat_score",
            "avg_prov_stat_score",
            "avg_ml_score",
            "provider_risk_score",
            "provider_risk_level",
            "provider_narrative",
            "ai_pattern_deviation",
            "ai_velocity_indicator",
            "ai_recommendation",
        ]
    ]


def format_provider_id(raw_provider_id) -> str:
    raw = str(raw_provider_id or "").strip()
    if raw.startswith("PRV-"):
        return raw
    return f"PRV-{raw[-7:]}"


def provider_metadata(raw_provider_id) -> dict:
    return _provider_metadata(raw_provider_id)


def _provider_ai_summary(row: pd.Series) -> dict:
    if float(row.get("provider_risk_score", 0) or 0) > config.RISK_HIGH:
        return generate_for_provider(row.to_dict())
    return generate_for_provider(
        {**row.to_dict(), "provider_risk_level": row.get("provider_risk_level", "Low")},
        use_openai=False,
    )


def _provider_metadata(raw_provider_id) -> dict:
    seed = int(hashlib.sha256(str(raw_provider_id).encode("utf-8")).hexdigest(), 16)
    city, state = CITIES[seed % len(CITIES)]
    return {
        "name": PRACTICE_NAMES[seed % len(PRACTICE_NAMES)],
        "specialty": SPECIALTIES[(seed // 7) % len(SPECIALTIES)],
        "city": city,
        "state": state,
    }
