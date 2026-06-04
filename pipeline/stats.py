from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from pipeline import config


def compute_zscore(series: pd.Series) -> pd.Series:
    mean = series.mean()
    std = series.std()
    if pd.isna(std) or std == 0:
        return (series - mean) * 0
    return (series - mean) / std


def _norm(raw: pd.Series) -> pd.Series:
    max_value = raw.max()
    if pd.isna(max_value) or max_value == 0:
        return raw * 0
    return (100 * raw / max_value).clip(0, 100)


def apply_statistical_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Compute claim and provider statistical scores."""
    out = df.copy()
    out["Z_AllowedAmount"] = compute_zscore(out["AmtAllowed"].fillna(0))
    out["Z_Units"] = compute_zscore(out["Units"].fillna(0))
    out["Z_BilledToAllowed"] = compute_zscore(out["BilledAmountToAllowedRatio"].fillna(0))

    claim_raw = (
        out["Z_AllowedAmount"].abs() * 30
        + out["Z_Units"].abs() * 20
        + out["Z_BilledToAllowed"].abs() * 50
    )
    out["Claim_Stat_Score"] = _norm(claim_raw)

    provider_means = (
        out.groupby("ProviderId", dropna=False)[["AmtAllowed", "Units", "BilledAmountToAllowedRatio"]]
        .mean()
        .rename(
            columns={
                "AmtAllowed": "Prov_Avg_Allowed",
                "Units": "Prov_Avg_Units",
                "BilledAmountToAllowedRatio": "Prov_Avg_Ratio",
            }
        )
    )
    provider_means["Z_Prov_Allowed"] = compute_zscore(provider_means["Prov_Avg_Allowed"])
    provider_means["Z_Prov_Units"] = compute_zscore(provider_means["Prov_Avg_Units"])
    provider_means["Z_Prov_Ratio"] = compute_zscore(provider_means["Prov_Avg_Ratio"])
    provider_raw = (
        provider_means["Z_Prov_Allowed"].abs() * 40
        + provider_means["Z_Prov_Units"].abs() * 20
        + provider_means["Z_Prov_Ratio"].abs() * 40
    )
    provider_means["Provider_Stat_Score"] = _norm(provider_raw)

    out = out.merge(
        provider_means[["Z_Prov_Allowed", "Z_Prov_Units", "Z_Prov_Ratio", "Provider_Stat_Score"]],
        left_on="ProviderId",
        right_index=True,
        how="left",
    )
    out["ML_Flag"] = (out["Claim_Stat_Score"] > config.ML_FLAG_CLAIM_SCORE_THRESHOLD) | (
        out["Provider_Stat_Score"] > config.ML_FLAG_PROVIDER_SCORE_THRESHOLD
    )
    out["Stat_Narrative"] = out.apply(_stat_narrative, axis=1)
    return out


def score_single_claim(claim_dict: dict, population_stats: dict) -> dict:
    """Score one claim against population stats cached from historical claims."""
    claim = claim_dict.copy()
    claim["Z_AllowedAmount"] = _single_z(claim.get("AmtAllowed", 0), population_stats.get("amt_allowed_mean"), population_stats.get("amt_allowed_std"))
    claim["Z_Units"] = _single_z(claim.get("Units", 0), population_stats.get("units_mean"), population_stats.get("units_std"))
    claim["Z_BilledToAllowed"] = _single_z(
        claim.get("BilledAmountToAllowedRatio", 0),
        population_stats.get("billed_ratio_mean"),
        population_stats.get("billed_ratio_std"),
    )
    raw = (
        abs(claim["Z_AllowedAmount"]) * 30
        + abs(claim["Z_Units"]) * 20
        + abs(claim["Z_BilledToAllowed"]) * 50
    )
    claim["Claim_Stat_Score"] = _clip_score(raw, population_stats.get("claim_stat_raw_max", 100))

    provider_key = str(claim.get("ProviderId", ""))
    provider_stats = population_stats.get("provider_stats", {}).get(provider_key)
    if provider_stats:
        claim["Z_Prov_Allowed"] = provider_stats.get("z_allowed", 0)
        claim["Z_Prov_Units"] = provider_stats.get("z_units", 0)
        claim["Z_Prov_Ratio"] = provider_stats.get("z_ratio", 0)
        claim["Provider_Stat_Score"] = provider_stats.get("score", 0)
    else:
        claim["Z_Prov_Allowed"] = claim["Z_AllowedAmount"]
        claim["Z_Prov_Units"] = claim["Z_Units"]
        claim["Z_Prov_Ratio"] = claim["Z_BilledToAllowed"]
        provider_raw = (
            abs(claim["Z_Prov_Allowed"]) * 40
            + abs(claim["Z_Prov_Units"]) * 20
            + abs(claim["Z_Prov_Ratio"]) * 40
        )
        claim["Provider_Stat_Score"] = _clip_score(provider_raw, population_stats.get("provider_stat_raw_max", 100))

    claim["ML_Flag"] = (claim["Claim_Stat_Score"] > config.ML_FLAG_CLAIM_SCORE_THRESHOLD) or (
        claim["Provider_Stat_Score"] > config.ML_FLAG_PROVIDER_SCORE_THRESHOLD
    )
    claim["Stat_Narrative"] = _stat_narrative(pd.Series(claim))
    return claim


def get_population_stats(db: Session) -> dict:
    """Load population means/stds and provider score context from the claims table."""
    from db.models import Claim

    rows = db.query(
        Claim.provider_id,
        Claim.amt_allowed,
        Claim.units_used,
        Claim.billed_amount_to_allowed_ratio,
        Claim.claim_stat_score,
        Claim.provider_stat_score,
        Claim.z_allowed_amount,
        Claim.z_units,
        Claim.z_billed_to_allowed,
    ).all()
    if not rows:
        return {}

    df = pd.DataFrame(
        rows,
        columns=[
            "provider_id",
            "amt_allowed",
            "units",
            "billed_ratio",
            "claim_stat_score",
            "provider_stat_score",
            "z_allowed",
            "z_units",
            "z_ratio",
        ],
    ).fillna(0)
    claim_raw = (
        df["z_allowed"].abs() * 30 + df["z_units"].abs() * 20 + df["z_ratio"].abs() * 50
    )
    provider_group = df.groupby("provider_id", dropna=False).agg(
        z_allowed=("z_allowed", "mean"),
        z_units=("z_units", "mean"),
        z_ratio=("z_ratio", "mean"),
        score=("provider_stat_score", "mean"),
    )
    provider_raw = (
        provider_group["z_allowed"].abs() * 40
        + provider_group["z_units"].abs() * 20
        + provider_group["z_ratio"].abs() * 40
    )
    return {
        "amt_allowed_mean": float(df["amt_allowed"].mean()),
        "amt_allowed_std": float(df["amt_allowed"].std() or 0),
        "units_mean": float(df["units"].mean()),
        "units_std": float(df["units"].std() or 0),
        "billed_ratio_mean": float(df["billed_ratio"].mean()),
        "billed_ratio_std": float(df["billed_ratio"].std() or 0),
        "claim_stat_raw_max": float(claim_raw.max() or 100),
        "provider_stat_raw_max": float(provider_raw.max() or 100),
        "provider_stats": provider_group.to_dict(orient="index"),
    }


def _single_z(value: Any, mean: Any, std: Any) -> float:
    std = float(std or 0)
    if std == 0:
        return 0.0
    return float((float(value or 0) - float(mean or 0)) / std)


def _clip_score(raw: float, max_raw: Any) -> float:
    max_raw = float(max_raw or 0)
    if max_raw == 0:
        return 0.0
    return float(np.clip(100 * raw / max_raw, 0, 100))


def _stat_narrative(row: pd.Series) -> str:
    signals = []
    if abs(float(row.get("Z_AllowedAmount", 0) or 0)) >= config.NARRATIVE_ZSCORE_THRESHOLD:
        signals.append(f"Allowed amount is {row.get('Z_AllowedAmount', 0):.1f} SD from the population mean.")
    if abs(float(row.get("Z_BilledToAllowed", 0) or 0)) >= config.NARRATIVE_ZSCORE_THRESHOLD:
        signals.append(f"Billed-to-allowed ratio is {row.get('Z_BilledToAllowed', 0):.1f} SD from the population mean.")
    if abs(float(row.get("Z_Prov_Allowed", 0) or 0)) >= config.NARRATIVE_ZSCORE_THRESHOLD:
        signals.append(f"Provider allowed amount behavior is {row.get('Z_Prov_Allowed', 0):.1f} SD from peers.")
    return " ".join(signals) if signals else "Claim and provider statistics are within expected ranges."

