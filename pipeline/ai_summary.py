from __future__ import annotations

import json
import os
import time

import pandas as pd
from openai import OpenAI

from pipeline import config


SYSTEM_PROMPT = """You are a healthcare fraud analyst AI assistant for an insurance SIU team.
Given structured claim analysis data, generate a concise professional investigation summary.
Use business language for analysts. Do not mention procedure code, z-score, SD, mean, Isolation Forest, PCA, reconstruction, or model internals.
Respond ONLY with valid JSON. Keys: summary, riskReasoning, recommendation, patternSummary.
Each value must be a string under 100 words. Do not include any other text.
The patternSummary must use a professional enterprise fraud review tone and clearly explain: the detected pattern concern, the key contributing factors, and the recommended review actions. Keep it natural, actionable, concise, and easy for claim reviewers to understand. Do not mention procedure codes."""

PROVIDER_SYSTEM_PROMPT = """You are a healthcare fraud analyst AI assistant for an insurance SIU team.
Given provider-level claims analytics, generate concise provider monitoring guidance.
Respond ONLY with valid JSON. Keys: patternDeviation, velocityIndicator, recommendation.
Each value must be a string under 100 words. Do not include any other text."""

OPENAI_BASE_URL = "https://d2brdeqy144bwg.cloudfront.net/myllm/v1"


def generate_for_claim(claim_data: dict) -> dict:
    """Call ChatOpenAI and return an investigation summary, with fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", config.OPENAI_MODEL_DEFAULT)
    if not api_key:
        return _with_llm_metadata(_fallback_summary(claim_data), False, model, "missing_openai_api_key")

    user_content = f"""
Claim Analysis:
- Procedure: {claim_data.get('ProcedureCode')} | Allowed: ${claim_data.get('AmtAllowed')}
- Member Age: {claim_data.get('MemberAge', claim_data.get('PatientAge'))} | Provider: {claim_data.get('ProviderId')}
- Rule Score: {claim_data.get('Rule_Score_Total', 0)}/29 | Rules triggered: {claim_data.get('Rule_Narrative', 'None')}
- Claim history concern score: {float(claim_data.get('Claim_Stat_Score_Norm', claim_data.get('Claim_Stat_Score', 0)) or 0):.1f}/100
- Provider peer concern score: {float(claim_data.get('Provider_Stat_Score_Norm', claim_data.get('Provider_Stat_Score', 0)) or 0):.1f}/100
- Payment behavior concern score: {float(claim_data.get('IF_Score_Norm', 0) or 0):.1f}/100
- Claim detail consistency concern score: {float(claim_data.get('PCA_Score_Norm', 0) or 0):.1f}/100
- Pattern review narrative: {claim_data.get('ML_Anomaly_Narrative', 'None')}
- Final Score: {float(claim_data.get('Final_Combined_Score', 0) or 0):.1f}/100
- Risk Level: {claim_data.get('Final_Risk_Level')}
- Suspected Fraud Type: {claim_data.get('Final_Fraud_Type')}

Generate the investigation summary JSON. For patternSummary, avoid repetitive wording, robotic phrases, overly technical language, and procedure codes.
"""
    try:
        client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        return {
            "summary": str(parsed.get("summary", "")),
            "riskReasoning": str(parsed.get("riskReasoning", "")),
            "recommendation": str(parsed.get("recommendation", "")),
            "patternSummary": str(parsed.get("patternSummary", "")),
            "llmGenerated": True,
            "model": model,
        }
    except Exception as exc:
        return _with_llm_metadata(_fallback_summary(claim_data), False, model, exc.__class__.__name__)


def generate_batch(df: pd.DataFrame, score_threshold: float = config.AI_SUMMARY_SCORE_THRESHOLD) -> pd.DataFrame:
    """Generate summaries for a batch, calling OpenAI only for Medium+ claims."""
    out = df.copy()
    summaries = []
    generated_flags = []
    for _, row in out.iterrows():
        if row["Final_Combined_Score"] >= score_threshold:
            summary = generate_for_claim(row.to_dict())
            generated_flags.append(bool(summary.get("llmGenerated")))
            time.sleep(config.AI_RATE_LIMIT_SLEEP)
        else:
            summary = _low_risk_summary()
            generated_flags.append(False)
        summaries.append(json.dumps(summary))
    out["ai_summary"] = summaries
    out["ai_summary_generated"] = generated_flags
    return out


def generate_for_provider(provider_data: dict, use_openai: bool = True) -> dict:
    """Call ChatOpenAI for provider-level analysis, with deterministic fallback."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not use_openai or not api_key:
        return _fallback_provider_summary(provider_data)

    user_content = f"""
Provider Analysis:
- Provider: {provider_data.get('id')} | {provider_data.get('name')}
- Specialty: {provider_data.get('specialty')} | Location: {provider_data.get('city')}, {provider_data.get('state')}
- Total Claims: {provider_data.get('total_claims')}
- Total Allowed: ${float(provider_data.get('total_allowed', 0) or 0):.2f}
- High Risk Ratio: {float(provider_data.get('high_risk_ratio', 0) or 0):.1%}
- Avg Final Score: {float(provider_data.get('avg_final_score', 0) or 0):.1f}/100
- Avg ML Score: {float(provider_data.get('avg_ml_score', 0) or 0):.1f}/100
- Avg Provider Stat Score: {float(provider_data.get('avg_prov_stat_score', 0) or 0):.1f}/100
- Provider Risk Score: {float(provider_data.get('provider_risk_score', 0) or 0):.1f}/100
- Provider Risk Level: {provider_data.get('provider_risk_level')}

Generate provider monitoring JSON.
"""
    try:
        client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", config.OPENAI_MODEL_DEFAULT),
            messages=[
                {"role": "system", "content": PROVIDER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        parsed = json.loads(response.choices[0].message.content.strip())
        return {
            "patternDeviation": str(parsed.get("patternDeviation", "")),
            "velocityIndicator": str(parsed.get("velocityIndicator", "")),
            "recommendation": str(parsed.get("recommendation", "")),
        }
    except Exception:
        return _fallback_provider_summary(provider_data)


def _fallback_summary(claim_data: dict) -> dict:
    risk_level = claim_data.get("Final_Risk_Level", "Low")
    score = float(claim_data.get("Final_Combined_Score", 0) or 0)
    procedure = claim_data.get("ProcedureCode") or "the submitted procedure"
    allowed = float(claim_data.get("AmtAllowed", 0) or 0)
    charged = float(claim_data.get("AmtCharged", 0) or 0)
    rule_score = float(claim_data.get("Rule_Score_Total", 0) or 0)
    rule_score_norm = float(claim_data.get("Rule_Score_Norm", 0) or 0)
    claim_stat = float(claim_data.get("Claim_Stat_Score_Norm", claim_data.get("Claim_Stat_Score", 0)) or 0)
    provider_stat = float(claim_data.get("Provider_Stat_Score_Norm", claim_data.get("Provider_Stat_Score", 0)) or 0)
    ml_score = float(claim_data.get("ML_Anomaly_Score_Norm", claim_data.get("ML_Anomaly_Score", 0)) or 0)
    fraud_type = claim_data.get("Final_Fraud_Type") or "No Significant Fraud Indicators"
    rule_text = claim_data.get("Rule_Narrative") or "No deterministic rules triggered."
    stat_text = claim_data.get("Stat_Narrative") or "Historical comparison did not add a separate concern narrative."
    ml_text = claim_data.get("ML_Anomaly_Narrative") or "Pattern review did not add a separate concern narrative."
    primary_driver = max(
        [
            ("rules engine", rule_score_norm),
            ("claim history comparison", claim_stat),
            ("provider peer comparison", provider_stat),
            ("pattern review", ml_score),
        ],
        key=lambda item: item[1],
    )
    return {
        "summary": (
            f"{risk_level} priority review for {procedure}: final score {score:.1f}/100, likely issue "
            f"{fraud_type}. The claim allowed amount is ${allowed:,.2f} against ${charged:,.2f} billed."
        ),
        "riskReasoning": (
            f"The largest driver is the {primary_driver[0]} at {primary_driver[1]:.1f}/100. "
            f"Rules engine score is {rule_score:.1f}/{config.MAX_RULE_SCORE} ({rule_score_norm:.1f}/100): {rule_text} "
            f"Historical comparison: {stat_text} Pattern review: {ml_text}"
        ),
        "recommendation": (
            "Route to SIU review with the rules, historical comparison, and pattern review details attached for analyst validation."
            if risk_level in ["High", "Critical"]
            else "Continue standard adjudication, retaining the generated reasoning for audit trail review."
        ),
        "patternSummary": _fallback_pattern_summary(claim_data),
    }


def _low_risk_summary() -> dict:
    return {
        "summary": "Low risk claim. No significant fraud indicators detected.",
        "riskReasoning": "Rule, historical comparison, and pattern checks stayed within configured thresholds.",
        "recommendation": "Auto-adjudicate.",
        "patternSummary": (
            "Pattern review did not identify a material behavioral concern. Amount, unit, and claim detail signals are aligned with expected activity; proceed through standard adjudication controls."
        ),
    }


def _fallback_pattern_summary(claim_data: dict) -> str:
    ml_score = float(claim_data.get("ML_Anomaly_Score_Norm", claim_data.get("ML_Anomaly_Score", 0)) or 0)
    payment_score = float(claim_data.get("IF_Score_Norm", 0) or 0)
    detail_score = float(claim_data.get("PCA_Score_Norm", 0) or 0)

    factors = []
    if payment_score >= 50:
        factors.append("payment behavior is outside the expected range")
    if detail_score >= 50:
        factors.append("claim details do not fully align with prior patterns")
    if not factors:
        factors.append("amount, unit, and service detail signals remain generally consistent")

    if ml_score >= 50:
        return (
            "Pattern review indicates elevated concern based on how this claim compares with prior billing behavior. "
            f"Key contributors include {', and '.join(factors)}, which may point to a change in billing profile or documentation support. "
            "Reviewers should verify the submitted documentation, unit count, allowed amount, and provider billing context before release."
        )

    return (
        "Pattern review does not indicate a material behavioral concern. "
        f"The main signals show that {', and '.join(factors)}. "
        "Reviewers can continue standard adjudication unless rules, history, or provider context raise a separate concern."
    )


def _fallback_provider_summary(provider_data: dict) -> dict:
    risk_level = provider_data.get("provider_risk_level", "Low")
    return {
        "patternDeviation": (
            f"Billing risk is driven by average fraud score "
            f"{float(provider_data.get('avg_final_score', 0) or 0):.1f} and pattern review score "
            f"{float(provider_data.get('avg_ml_score', 0) or 0):.1f}."
        ),
        "velocityIndicator": (
            f"{int(provider_data.get('total_claims', 0) or 0)} claims observed in the loaded historical population."
        ),
        "recommendation": "Prioritize for SIU review." if risk_level in ["High", "Critical"] else "Continue routine monitoring.",
    }


def _with_llm_metadata(summary: dict, generated: bool, model: str, reason: str | None = None) -> dict:
    out = summary.copy()
    out["llmGenerated"] = generated
    out["model"] = model
    if reason:
        out["fallbackReason"] = reason
    return out
