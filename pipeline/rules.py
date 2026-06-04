from __future__ import annotations

import pandas as pd

from pipeline import config


RULE_COLUMNS = {
    "R001": "R001_Material_Upcoding",
    "R002": "R002_Material_Upcoding_Lens",
    "R003": "R003_Polycarb",
    "R004": "R004_Frame_Upcoding",
    "R005": "R005_Sunglasses",
    "R006": "R006_HighCost_Frames",
    "R007": "R007_HighCost_Lenses",
    "R008": "R008_HighCost_Materials",
    "R009": "R009_High_Billed_Ratio",
    "R010": "R010_High_Units",
    "R011": "R011_Young_Member",
}

RULE_MESSAGES = {
    "R001": "Premium material code V2700-V2799 detected; possible material upcoding.",
    "R002": "Lens material code V21X-V23X detected; possible lens material upcoding.",
    "R003": "Polycarbonate code detected; verify medical necessity.",
    "R004": "Frame code V2020/V2025 detected with upcoding risk.",
    "R005": "Sunglasses/tint code V2744 detected.",
    "R006": "High-cost frame allowed amount exceeds threshold.",
    "R007": "High-cost lens allowed amount exceeds threshold.",
    "R008": "High-cost material allowed amount exceeds threshold.",
    "R009": "Billed-to-allowed ratio exceeds threshold.",
    "R010": "Units exceed expected utilization threshold.",
    "R011": "Young member with high-cost material claim.",
}


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Apply rules R001-R011 and return a DataFrame with boolean flags."""
    out = df.copy()
    proc = out["ProcedureCode"].fillna("").astype(str).str.upper()
    service = out["ServiceCategoryName"].fillna("").astype(str)
    benefit = out["BenefitCategoryName"].fillna("").astype(str)

    out[RULE_COLUMNS["R001"]] = proc.str.match(r"V27\d{2}", na=False)
    out[RULE_COLUMNS["R002"]] = proc.str.match(r"V2[1-3]\d", na=False)
    out[RULE_COLUMNS["R003"]] = proc.isin(["V2763", "V2764"])
    out[RULE_COLUMNS["R004"]] = proc.isin(["V2020", "V2025"])
    out[RULE_COLUMNS["R005"]] = proc.eq("V2744")
    out[RULE_COLUMNS["R006"]] = service.str.contains("frame", case=False, na=False) & (
        out["AmtAllowed"] > config.THRESHOLD_HIGHCOST_FRAME
    )
    out[RULE_COLUMNS["R007"]] = service.str.contains("lens", case=False, na=False) & (
        out["AmtAllowed"] > config.THRESHOLD_HIGHCOST_LENS
    )
    out[RULE_COLUMNS["R008"]] = benefit.str.contains("material", case=False, na=False) & (
        out["AmtAllowed"] > config.THRESHOLD_HIGHCOST_MATERIAL
    )
    out[RULE_COLUMNS["R009"]] = out["BilledAmountToAllowedRatio"] > config.THRESHOLD_BILLED_RATIO
    out[RULE_COLUMNS["R010"]] = out["Units"] > config.THRESHOLD_HIGH_UNITS
    out[RULE_COLUMNS["R011"]] = (
        (out["PatientAge"] < config.THRESHOLD_YOUNG_MEMBER_AGE)
        & (out["AmtAllowed"] > config.THRESHOLD_HIGHCOST_MATERIAL)
        & benefit.str.contains("material", case=False, na=False)
    )
    out["Rule_Flag_Count"] = out[list(RULE_COLUMNS.values())].sum(axis=1).astype(int)
    return out


def generate_rule_narratives(df: pd.DataFrame) -> pd.DataFrame:
    """Generate rule narrative list and display text."""
    out = df.copy()

    def row_messages(row: pd.Series) -> list[dict]:
        messages = []
        for code, column in RULE_COLUMNS.items():
            if bool(row.get(column, False)):
                messages.append(
                    {
                        "ruleCode": code,
                        "severity": _severity_for_weight(config.RULE_WEIGHTS[code]),
                        "message": RULE_MESSAGES[code],
                    }
                )
        return messages

    narratives = out.apply(row_messages, axis=1)
    out["Rule_Narrative_List"] = narratives
    out["Rule_Narrative"] = narratives.apply(
        lambda items: " | ".join(f"{item['ruleCode']}: {item['message']}" for item in items)
        if items
        else "No deterministic rules triggered."
    )
    return out


def apply_rule_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """Apply documented severity weights and compute Rule_Score_Total."""
    out = df.copy()
    total = 0
    for code, column in RULE_COLUMNS.items():
        total = total + out[column].astype(int) * config.RULE_WEIGHTS[code]
    out["Rule_Score_Total"] = total.astype(float)
    return out


def apply_rules_single(claim: dict) -> dict:
    """Single-claim wrapper around the batch rule engine."""
    df = pd.DataFrame([claim])
    df = apply_rules(df)
    df = generate_rule_narratives(df)
    df = apply_rule_scoring(df)
    return df.iloc[0].to_dict()


def _severity_for_weight(weight: int) -> str:
    if weight >= 4:
        return "critical"
    if weight >= 3:
        return "high"
    if weight >= 2:
        return "medium"
    return "low"

