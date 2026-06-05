from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any, Optional

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from db.models import Claim, Notification, PipelineRun, ProviderGold


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
    page_size: int = 25,
    sort_by: str = "fraudScore",
    sort_dir: str = "desc",
) -> dict:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    query = db.query(Claim)

    if search:
        term = f"%{search}%"
        query = query.filter(or_(Claim.id.ilike(term), Claim.provider_id.ilike(term), Claim.procedure_code.ilike(term)))
    if risk_level:
        query = query.filter(Claim.final_risk_level == risk_level)
    if provider_id:
        query = query.filter(Claim.provider_id == provider_id)
    if procedure_code:
        query = query.filter(Claim.procedure_code == procedure_code)
    if fraud_type:
        query = query.filter(Claim.final_fraud_type == fraud_type)
    if status:
        query = query.filter(Claim.status == status)
    if min_fraud_score is not None:
        query = query.filter(Claim.final_combined_score >= min_fraud_score)
    if max_fraud_score is not None:
        query = query.filter(Claim.final_combined_score <= max_fraud_score)
    if date_from:
        query = query.filter(Claim.service_date >= date_from)
    if date_to:
        query = query.filter(Claim.service_date <= date_to)

    total = query.count()
    sort_column = _claim_sort_column(sort_by)
    query = query.order_by(desc(sort_column) if sort_dir != "asc" else asc(sort_column))
    items = query.offset((page - 1) * page_size).limit(page_size).all()

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
    claim = db.get(Claim, claim_id)
    if not claim:
        return None
    provider = db.get(ProviderGold, claim.provider_id)
    return build_claim_analysis(claim, provider)


def flag_claim(db: Session, claim_id: str) -> Optional[dict]:
    claim = db.get(Claim, claim_id)
    if not claim:
        return None
    claim.status = "Investigating"
    claim.flagged_at = datetime.utcnow()
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
        "status": claim.status,
        "queue": "SIU",
        "flaggedAt": claim.flagged_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
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


def build_claim_analysis(claim: Claim, provider: Optional[ProviderGold] = None) -> dict:
    ai_summary = _json_or_default(claim.ai_summary, {})
    cluster = CLUSTER_DEFINITIONS.get(claim.cluster_id or "CL-00", CLUSTER_DEFINITIONS["CL-00"]).copy()
    cluster["claimCount"] = 0
    return {
        "claim": claim_summary(claim),
        "analysis": {
            "pipeline": _pipeline_context(claim),
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
                "ruleScore": claim.rule_score_norm or 0,
                "severity": claim.final_risk_level or "Low",
                "triggeredRules": _triggered_rules(claim.rule_narrative),
            },
            "statisticalAnalysis": {
                "claimAmountZScore": claim.z_allowed_amount or 0,
                "providerZScore": claim.z_allowed_amount or 0,
                "narrative": claim.stat_narrative or "",
                "providerPercentile": min(100, round((claim.provider_stat_score or 0), 1)),
            },
            "mlAnalysis": {
                "anomalyScore": claim.ml_anomaly_score_norm or 0,
                "isolationForestScore": claim.if_score_norm or 0,
                "pcaErrorScore": claim.pca_score_norm or 0,
                "modelSummary": claim.ml_anomaly_narrative or "",
            },
            "clusterAssignment": {
                "clusterId": claim.cluster_id or "CL-00",
                "matched": (claim.cluster_id or "CL-00") != "CL-00",
                "confidence": min(0.99, max(0.0, (claim.final_combined_score or 0) / 100)),
                "cluster": cluster,
            },
            "aiSummary": ai_summary,
            "actions": {"canDownloadReport": True, "canFlagForSiu": True, "canAssignAnalyst": True},
        },
    }


def build_single_claim_analysis(claim_data: dict) -> dict:
    claim = _ad_hoc_claim(claim_data)
    return build_claim_analysis(claim, None)


def _ad_hoc_claim(data: dict) -> Claim:
    return Claim(
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
        status=data.get("status", "Pending"),
    )


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


def _json_or_default(raw: Optional[str], default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _claim_sort_column(sort_by: str):
    return {
        "fraudScore": Claim.final_combined_score,
        "allowedAmount": Claim.amt_allowed,
        "date": Claim.service_date,
        "riskLevel": Claim.final_risk_level,
    }.get(sort_by, Claim.final_combined_score)


def _notification_id() -> str:
    from uuid import uuid4

    return f"NTF-{str(uuid4())[:8].upper()}"
