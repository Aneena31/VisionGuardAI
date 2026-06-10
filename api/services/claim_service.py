from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any, Optional

from sqlalchemy.orm import Session

from api.services.historical_data_service import get_historical_data
from db.models import Claim, Notification, ProviderGold
from pipeline import config
from pipeline.rules import RULE_COLUMNS


CLUSTER_DEFINITIONS = {
    "CL-01": {
        "id": "CL-01",
        "name": "Phantom Billing",
        "riskCharacteristics": "Services billed for which no encounter occurred.",
        "claimCount": 0,
    },
    "CL-02": {
        "id": "CL-02",
        "name": "Upcoding - Exam",
        "riskCharacteristics": "Billing for a more complex or costly service than supported by claim context.",
        "claimCount": 0,
    },
    "CL-03": {
        "id": "CL-03",
        "name": "Unbundling - Glaucoma Screening",
        "riskCharacteristics": "Provider-level billing patterns show procedure mix deviation from peers.",
        "claimCount": 0,
    },
    "CL-00": {
        "id": "CL-00",
        "name": "N/A",
        "riskCharacteristics": "No behavioral cluster assigned.",
        "claimCount": 0,
    },
}


def list_claims(
    db: Session,
    search: Optional[str] = None,
    risk_level: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    provider_id: Optional[str] = None,
    procedure_code: Optional[str] = None,
    fraud_type: Optional[str] = None,
    status: Optional[str] = None,
    min_fraud_score: Optional[float] = None,
    max_fraud_score: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "rowId",
    sort_dir: str = "asc",
) -> dict:
    t0 = time.perf_counter()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    print(
        f"[VisionGuard] claims list started page={page} pageSize={page_size} "
        f"search={search or ''} risk={risk_level or ''}",
        flush=True,
    )

    claims = [
        claim
        for claim in get_historical_data().claims
        if _matches_claim(
            claim,
            search,
            risk_level,
            date_from,
            date_to,
            provider_id,
            procedure_code,
            fraud_type,
            status,
            min_fraud_score,
            max_fraud_score,
        )
    ]

    total = len(claims)
    claims.sort(key=lambda claim: _claim_sort_value(claim, sort_by), reverse=sort_dir != "asc")
    items = claims[(page - 1) * page_size : page * page_size]
    print(
        f"[VisionGuard] claims list completed returned={len(items)} total={total:,} "
        f"duration={time.perf_counter() - t0:.3f}s",
        flush=True,
    )

    return {
        "items": [claim_summary(item) for item in items],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": ceil(total / page_size) if page_size else 0,
        },
        "filters": {
            "applied": {"search": search, "riskLevel": risk_level},
            "availableRiskLevels": ["Low", "Medium", "High", "Critical"],
            "availableStatuses": ["Pending", "Flagged", "Cleared", "Investigating"],
        },
    }


def get_claim_analysis(db: Session, claim_id: str) -> Optional[dict]:
    data = get_historical_data()
    claim = data.claims_by_id.get(claim_id)
    if not claim:
        return None
    provider = data.providers_by_id.get(claim.provider_id) if claim.provider_id else None
    return build_claim_analysis(claim, provider, data)


def flag_claim(db: Session, claim_id: str) -> Optional[dict]:
    claim = db.get(Claim, claim_id)
    if not claim:
        claim = get_historical_data().claims_by_id.get(claim_id)
    if not claim:
        return None
    flagged_at = datetime.utcnow()
    claim.status = "Investigating"
    claim.flagged_at = flagged_at
    notification = Notification(
        id=_notification_id(),
        type="claim_flagged",
        title="Claim routed to SIU",
        message=f"Claim {claim_id} was assigned to the SIU queue.",
        related_claim_id=claim_id,
        related_provider_id=claim.provider_id,
    )
    db.add(notification)
    db.commit()
    return {
        "claimId": claim_id,
        "status": "Investigating",
        "queue": "SIU",
        "flaggedAt": flagged_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def report_payload(claim_id: str) -> dict:
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    return {
        "claimId": claim_id,
        "reportId": f"RPT-{claim_id}",
        "downloadUrl": f"/visionguard/claims/{claim_id}/report/download",
        "expiresAt": expires.isoformat().replace("+00:00", "Z"),
    }


def claim_summary(claim: Claim) -> dict:
    return {
        "id": claim.id,
        "providerId": claim.provider_id,
        "providerName": claim.provider_name or claim.provider_id,
        "memberId": claim.member_id,
        "procedureCode": claim.procedure_code,
        "procedureDesc": claim.procedure_desc or "",
        "allowedAmount": claim.amt_allowed or 0,
        "fraudScore": round(claim.final_combined_score or 0, 1),
        "riskLevel": claim.final_risk_level or "Low",
        "fraudType": claim.final_fraud_type,
        "clusterId": claim.cluster_id or "CL-00",
        "date": claim.service_date.isoformat() if claim.service_date else None,
        "status": claim.status or "Pending",
    }


def build_claim_analysis(claim: Claim, provider: Optional[ProviderGold] = None, historical_data: Any = None) -> dict:
    ai_summary = _json_or_default(claim.ai_summary, {})
    cluster = CLUSTER_DEFINITIONS.get(claim.cluster_id or "CL-00", CLUSTER_DEFINITIONS["CL-00"]).copy()
    cluster["claimCount"] = _cluster_claim_count(historical_data, claim.cluster_id or "CL-00")
    claim_pattern_score = _score_value(getattr(claim, "claim_stat_score_norm", None), claim.claim_stat_score)
    provider_pattern_score = _score_value(getattr(claim, "provider_stat_score_norm", None), claim.provider_stat_score)
    ml_pattern_score = _score_value(getattr(claim, "ml_anomaly_score_norm", None), claim.ml_anomaly_score)
    closest_case = _closest_case_for_claim(claim, historical_data)
    triggered_rules = _triggered_rules(claim.rule_narrative)
    total_rules = len(RULE_COLUMNS)
    failed_rules = min(total_rules, max(0, int(claim.rule_flag_count or len(triggered_rules))))
    passed_rules = max(0, total_rules - failed_rules)
    cluster_matched = (claim.cluster_id or "CL-00") != "CL-00"
    process_insights = _process_insights(
        claim,
        triggered_rules,
        total_rules,
        passed_rules,
        failed_rules,
        claim_pattern_score,
        provider_pattern_score,
        ml_pattern_score,
    )
    return {
        "claim": claim_summary(claim),
        "analysis": {
            "pipeline": _pipeline_context(claim),
            "processInsights": process_insights,
            "member": {
                "memberId": claim.member_id,
                "age": claim.member_age,
                "gender": claim.member_gender,
                "location": {"city": provider.city if provider else "", "state": provider.state if provider else ""},
            },
            "providerContext": {
                "providerId": claim.provider_id,
                "providerName": claim.provider_name or (provider.name if provider else claim.provider_id),
                "specialty": provider.specialty if provider else "",
                "city": provider.city if provider else "",
                "state": provider.state if provider else "",
                "historicalZScore": claim.z_allowed_amount or 0,
                "historicalPercentile": min(100, round((claim.provider_stat_score or 0), 1)),
            },
            "procedure": {
                "code": claim.procedure_code,
                "description": claim.procedure_desc or "",
                "allowedAmount": claim.amt_allowed or 0,
            },
            "rulesAnalysis": {
                "engine": "Deterministic Engine",
                "status": "triggered" if (claim.rule_flag_count or 0) > 0 else "clear",
                "totalRules": total_rules,
                "passedRules": passed_rules,
                "failedRules": failed_rules,
                "ruleScore": claim.rule_score_norm or 0,
                "severity": claim.final_risk_level or "Low",
                "triggeredRules": triggered_rules,
            },
            "statisticalAnalysis": {
                "claimAmountZScore": claim.z_allowed_amount or 0,
                "providerZScore": getattr(claim, "z_prov_allowed", claim.z_allowed_amount) or 0,
                "claimPatternScore": claim_pattern_score,
                "providerPatternScore": provider_pattern_score,
                "claimPatternLevel": _history_level(claim_pattern_score),
                "providerPatternLevel": _history_level(provider_pattern_score),
                "narrative": _business_stat_narrative(claim, claim_pattern_score),
                "providerPercentile": min(100, round((claim.provider_stat_score or 0), 1)),
            },
            "mlAnalysis": {
                "anomalyScore": ml_pattern_score,
                "isolationForestScore": claim.if_score_norm or 0,
                "pcaErrorScore": claim.pca_score_norm or 0,
                "concernLevel": _score_concern_label(ml_pattern_score),
                "modelSummary": _business_ml_narrative(claim),
            },
            "clusterAssignment": {
                "clusterId": claim.cluster_id or "CL-00",
                "matched": cluster_matched,
                "confidence": min(0.99, max(0.0, (claim.final_combined_score or 0) / 100)),
                "cluster": cluster,
                "closestCase": closest_case,
            },
            "aiSummary": ai_summary,
            "actions": {"canDownloadReport": True, "canFlagForSiu": True, "canAssignAnalyst": True},
        },
    }


def build_single_claim_analysis(claim_data: dict) -> dict:
    claim = _ad_hoc_claim(claim_data)
    claim.closest_similar_claim = claim_data.get("Closest_Similar_Claim")
    return build_claim_analysis(claim, None)


def _ad_hoc_claim(data: dict) -> Claim:
    claim = Claim(
        id=data.get("ClaimId", data.get("id", "")),
        provider_id=data.get("ProviderId", ""),
        provider_name=data.get("ProviderName", data.get("ProviderId", "")),
        member_id=data.get("MemberId", ""),
        member_age=int(data.get("PatientAge", data.get("MemberAge", 0)) or 0),
        member_gender=data.get("MemberGender", ""),
        procedure_code=data.get("ProcedureCode", ""),
        procedure_desc=data.get("ProcedureDesc", ""),
        benefit_type=data.get("BenefitType", "Other"),
        service_category_name=data.get("ServiceCategoryName", ""),
        benefit_category_name=data.get("BenefitCategoryName", ""),
        service_date=None,
        amt_charged=float(data.get("AmtCharged", 0) or 0),
        amt_allowed=float(data.get("AmtAllowed", 0) or 0),
        units_used=float(data.get("Units", 0) or 0),
        billed_amount_to_allowed_ratio=float(data.get("BilledAmountToAllowedRatio", 0) or 0),
        rule_flag_count=int(data.get("Rule_Flag_Count", 0) or 0),
        rule_score_total=float(data.get("Rule_Score_Total", 0) or 0),
        rule_narrative=data.get("Rule_Narrative", ""),
        z_allowed_amount=float(data.get("Z_AllowedAmount", 0) or 0),
        z_units=float(data.get("Z_Units", 0) or 0),
        z_billed_to_allowed=float(data.get("Z_BilledToAllowed", 0) or 0),
        claim_stat_score=float(data.get("Claim_Stat_Score", 0) or 0),
        provider_stat_score=float(data.get("Provider_Stat_Score", 0) or 0),
        stat_narrative=data.get("Stat_Narrative", ""),
        if_score_norm=float(data.get("IF_Score_Norm", 0) or 0),
        pca_score_norm=float(data.get("PCA_Score_Norm", 0) or 0),
        ml_anomaly_score=float(data.get("ML_Anomaly_Score", 0) or 0),
        ml_anomaly_score_norm=float(data.get("ML_Anomaly_Score_Norm", 0) or 0),
        ml_anomaly_narrative=data.get("ML_Anomaly_Narrative", ""),
        rule_score_norm=float(data.get("Rule_Score_Norm", 0) or 0),
        claim_stat_score_norm=float(data.get("Claim_Stat_Score_Norm", 0) or 0),
        provider_stat_score_norm=float(data.get("Provider_Stat_Score_Norm", 0) or 0),
        final_combined_score=float(data.get("Final_Combined_Score", 0) or 0),
        final_risk_level=data.get("Final_Risk_Level", "Low"),
        final_fraud_type=data.get("Final_Fraud_Type", ""),
        final_fraud_reason=data.get("Final_Fraud_Reason", ""),
        final_narrative=data.get("Final_Narrative", ""),
        ai_summary=json.dumps(data.get("ai_summary", {})),
        cluster_id=data.get("cluster_id", "CL-00"),
        similar_claim_ids=data.get("Similar_Claim_Ids", "[]"),
        status=data.get("status", "Pending"),
    )
    claim.z_prov_allowed = float(data.get("Z_Prov_Allowed", 0) or 0)
    claim.z_prov_units = float(data.get("Z_Prov_Units", 0) or 0)
    claim.z_prov_ratio = float(data.get("Z_Prov_Ratio", 0) or 0)
    return claim


def _pipeline_context(claim: Claim) -> dict:
    submitted = claim.created_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z") if claim.created_at else None
    return {
        "runId": "RUN-HISTORICAL",
        "status": "completed",
        "submittedAt": submitted,
        "completedAt": submitted,
        "statusText": "Pipeline execution completed",
    }


def _triggered_rules(rule_narrative: Optional[str]) -> list[dict]:
    if not rule_narrative or rule_narrative == "No deterministic rules triggered.":
        return []
    items = []
    for part in rule_narrative.split(" | "):
        if ":" in part:
            code, message = part.split(":", 1)
            items.append({"ruleCode": code.strip(), "severity": "high", "message": message.strip()})
    return items


def _process_insights(
    claim: Claim,
    triggered_rules: list[dict],
    total_rules: int,
    passed_rules: int,
    failed_rules: int,
    claim_pattern_score: float,
    provider_pattern_score: float,
    ml_pattern_score: float,
) -> list[str]:
    insights = []

    if failed_rules:
        insights.append(f"{failed_rules} rule violations found")
    else:
        insights.append("No rule violations")

    if claim_pattern_score >= 70 and provider_pattern_score >= 70:
        insights.append("Unusual claim and provider billing")
    elif claim_pattern_score >= 70:
        insights.append("Unusual claim billing")
    elif provider_pattern_score >= 70:
        insights.append("Unusual provider billing")
    elif claim_pattern_score >= 40 or provider_pattern_score >= 40:
        insights.append("Moderate billing variation")
    else:
        insights.append("Normal billing patterns")

    if ml_pattern_score >= 75:
        insights.append("High anomaly concern")
    elif ml_pattern_score >= 50:
        insights.append("Moderate anomaly concern")
    elif ml_pattern_score >= 25:
        insights.append("Low anomaly concern")
    else:
        insights.append("No anomaly concern")

    return insights


def _json_or_default(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _score_value(*values: Any) -> float:
    for value in values:
        try:
            if value is None:
                continue
            return min(100.0, max(0.0, round(float(value or 0), 1)))
        except (TypeError, ValueError):
            continue
    return 0.0


def _history_level(score: float) -> str:
    if score >= 70:
        return "Very unusual"
    if score >= 40:
        return "Moderate"
    return "Normal"


def _score_concern_label(score: float) -> str:
    if score >= 75:
        return "High concern"
    if score >= 50:
        return "Needs review"
    if score >= 25:
        return "Watch"
    return "Low concern"


def _business_stat_narrative(claim: Claim, claim_score: float) -> str:
    signals = []
    _add_history_signal(signals, claim.z_allowed_amount, "Allowed amount", "historical claims")
    _add_history_signal(signals, getattr(claim, "z_billed_to_allowed", 0), "Billed-to-allowed ratio", "historical claims")
    _add_history_signal(signals, getattr(claim, "z_units", 0), "Units billed", "historical claims")

    if signals:
        return " ".join(signals)
    if claim_score >= 70:
        return "The overall claim billing profile is unusual compared with historical claims."
    if claim_score >= 40:
        return "The claim has some differences from prior patterns, but not enough to make this a high-concern historical match."
    return "The claim looks consistent with expected historical billing patterns."


def _add_history_signal(signals: list[str], value: Any, label: str, comparison_group: str) -> None:
    try:
        numeric_value = float(value or 0)
    except (TypeError, ValueError):
        return
    if abs(numeric_value) < config.NARRATIVE_ZSCORE_THRESHOLD:
        return
    direction = "higher" if numeric_value > 0 else "lower"
    signals.append(f"{label} is {direction} than expected for {comparison_group}.")


def _business_ml_narrative(claim: Claim) -> str:
    score = _score_value(getattr(claim, "ml_anomaly_score_norm", None), claim.ml_anomaly_score)
    procedure = claim.procedure_code or "this procedure"
    if score >= 70:
        return f"High concern for {procedure}; the claim differs from prior behavior and should be reviewed."
    if score >= 40:
        return f"Needs review for {procedure}; the claim has noticeable differences from prior behavior."
    return f"Low concern for {procedure}; the claim is consistent with prior behavior."


def _cluster_claim_count(historical_data: Any, cluster_id: str) -> int:
    claims = getattr(historical_data, "claims", None)
    if not claims:
        return 0
    return sum(1 for item in claims if (item.cluster_id or "CL-00") == cluster_id)


def _closest_case_for_claim(claim: Claim, historical_data: Any) -> Optional[dict]:
    payload = getattr(claim, "closest_similar_claim", None)
    if isinstance(payload, dict):
        return payload

    similar_ids = _json_or_default(claim.similar_claim_ids, [])
    if not similar_ids:
        return None
    claims_by_id = getattr(historical_data, "claims_by_id", {}) if historical_data else {}
    for similar_id in similar_ids:
        candidate = claims_by_id.get(str(similar_id))
        if candidate and candidate.id != claim.id:
            return _similar_case_summary(candidate)
    return None


def _similar_case_summary(claim: Claim) -> dict:
    return {
        "id": claim.id,
        "providerId": claim.provider_id,
        "providerName": claim.provider_name or claim.provider_id,
        "procedureCode": claim.procedure_code,
        "procedureDesc": claim.procedure_desc or "",
        "allowedAmount": round(claim.amt_allowed or 0, 2),
        "billedAmount": round(claim.amt_charged or 0, 2),
        "billedToAllowedRatio": round(claim.billed_amount_to_allowed_ratio or 0, 2),
        "fraudScore": round(claim.final_combined_score or 0, 1),
        "riskLevel": claim.final_risk_level or "Low",
        "issueType": claim.final_fraud_type or "No significant issue",
        "clusterId": claim.cluster_id or "CL-00",
        "date": claim.service_date.isoformat() if claim.service_date else None,
        "status": claim.status or "Pending",
        "similarityScore": None,
        "matchReason": "closest processed historical claim profile",
    }


def _matches_claim(
    claim: Claim,
    search: Optional[str],
    risk_level: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    provider_id: Optional[str],
    procedure_code: Optional[str],
    fraud_type: Optional[str],
    status: Optional[str],
    min_fraud_score: Optional[float],
    max_fraud_score: Optional[float],
) -> bool:
    if search:
        term = search.lower()
        haystack = " ".join([claim.id or "", claim.provider_id or "", claim.provider_name or "", claim.procedure_code or ""]).lower()
        if term not in haystack:
            return False
    if risk_level and claim.final_risk_level != risk_level:
        return False
    if provider_id and claim.provider_id != provider_id:
        return False
    if procedure_code and claim.procedure_code != procedure_code:
        return False
    if fraud_type and claim.final_fraud_type != fraud_type:
        return False
    if status and (claim.status or "Pending") != status:
        return False
    if min_fraud_score is not None and (claim.final_combined_score or 0) < min_fraud_score:
        return False
    if max_fraud_score is not None and (claim.final_combined_score or 0) > max_fraud_score:
        return False
    if (date_from or date_to) and not claim.service_date:
        return False
    if date_from and claim.service_date.isoformat() < date_from:
        return False
    if date_to and claim.service_date.isoformat() > date_to:
        return False
    return True


def _claim_sort_value(claim: Claim, sort_by: str):
    if sort_by == "rowId":
        return claim.row_id or 0
    if sort_by == "allowedAmount":
        return claim.amt_allowed or 0
    if sort_by == "date":
        return claim.service_date or datetime.min.date()
    if sort_by == "riskLevel":
        return {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}.get(claim.final_risk_level or "Low", 0)
    if sort_by == "claimId":
        return claim.id or ""
    return claim.final_combined_score or 0


def _notification_id() -> str:
    from uuid import uuid4

    return f"NTF-{str(uuid4())[:8].upper()}"
