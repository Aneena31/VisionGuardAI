from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.database import SessionLocal, init_db
from db.models import Claim, Notification, PipelineRun, ProviderGold, ScoringJob
from pipeline import config, ml
from pipeline.aggregation import format_provider_id, provider_metadata
from pipeline.pipeline import run_batch


load_dotenv()


def seed() -> None:
    init_db()
    data_file = Path(os.getenv("DATA_FILE_PATH", str(config.DEFAULT_DATA_FILE_PATH)))
    artifacts_path = Path(os.getenv("ARTIFACTS_PATH", str(config.DEFAULT_ARTIFACTS_PATH)))
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    started_at = datetime.utcnow()
    run_id = f"RUN-{started_at:%Y%m%d}-001"
    db = SessionLocal()
    db.add(PipelineRun(id=run_id, status="running", started_at=started_at, claims_processed=0, claims_failed=0))
    db.commit()

    try:
        t0 = time.perf_counter()
        claims_df, provider_gold_df, artifacts = run_batch(str(data_file))
        ml.save_artifacts(
            artifacts["scaler"],
            artifacts["isolation_forest"],
            artifacts["pca"],
            artifacts["ml_features"],
            artifacts_path,
            artifacts["score_stats"],
        )

        db.query(Notification).delete()
        db.query(ScoringJob).delete()
        db.query(ProviderGold).delete()
        db.query(Claim).delete()
        db.commit()

        db.bulk_save_objects([_claim_from_row(row) for _, row in claims_df.iterrows()])
        db.bulk_save_objects([ProviderGold(**_provider_gold_payload(row)) for _, row in provider_gold_df.iterrows()])
        completed_at = datetime.utcnow()
        duration = time.perf_counter() - t0
        run = db.get(PipelineRun, run_id)
        run.status = "completed"
        run.claims_processed = int(len(claims_df))
        run.claims_failed = 0
        run.completed_at = completed_at
        run.duration_seconds = float(duration)
        db.commit()

        generated = int(claims_df.get("ai_summary_generated", pd.Series(dtype=bool)).fillna(False).sum())
        print("DB seeded successfully.")
        print(f"Claims persisted:     {len(claims_df):,}")
        print(f"Providers persisted:  {len(provider_gold_df):,}")
        print(f"AI summaries generated: {generated:,}")
        print(f"Duration: {duration:.1f} sec")
    except Exception as exc:
        run = db.get(PipelineRun, run_id)
        if run:
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()


def _claim_from_row(row: pd.Series) -> Claim:
    raw_claim_id = _int(row.get("ClaimId") or row.get("ClaimID") or row.get("claim_id") or row.get("row_id"))
    raw_provider_id = row.get("ProviderId", "")
    service_date = pd.to_datetime(row.get("ServiceMonth"), errors="coerce")
    service_py_date = None if pd.isna(service_date) else service_date.date()
    provider_id = format_provider_id(raw_provider_id)
    return Claim(
        id=f"CLM-{raw_claim_id}",
        raw_claim_id=raw_claim_id,
        row_id=_int(row.get("row_id")),
        provider_id=provider_id,
        provider_name=_provider_name(row, provider_id),
        member_id=_format_member_id(row.get("MemberId", row.get("MemberID", row.get("MemberNumber", "")))),
        member_age=_int(row.get("PatientAge")),
        member_gender=_str(row.get("MemberGender", row.get("Gender", ""))),
        subscriber_id=_str(row.get("SubscriberId", row.get("SubscriberID", ""))),
        group_id=_str(row.get("GroupId", row.get("GroupID", ""))),
        procedure_code=_str(row.get("ProcedureCode")),
        procedure_desc=_str(row.get("ProcedureDesc", row.get("ProcedureDescription", ""))),
        benefit_type=_str(row.get("BenefitType", "Other")),
        service_category_name=_str(row.get("ServiceCategoryName")),
        benefit_category_name=_str(row.get("BenefitCategoryName")),
        service_date=service_py_date,
        service_year=service_py_date.year if service_py_date else None,
        adjustment_version=_int(row.get("AdjustmentVersion")),
        line_number=_int(row.get("LineNumber")),
        amt_charged=_float(row.get("AmtCharged")),
        amt_allowed=_float(row.get("AmtAllowed")),
        paid_amount=_float(row.get("PaidAmount")),
        allowed_units=_float(row.get("AllowedUnits")),
        units_used=_float(row.get("Units")),
        utilization_pct_amt=_float(row.get("UtilizationPctAmt")),
        billed_amount_to_allowed_ratio=_float(row.get("BilledAmountToAllowedRatio")),
        r001_material_upcoding=_bool(row.get("R001_Material_Upcoding")),
        r002_material_upcoding_lens=_bool(row.get("R002_Material_Upcoding_Lens")),
        r003_polycarb=_bool(row.get("R003_Polycarb")),
        r004_frame_upcoding=_bool(row.get("R004_Frame_Upcoding")),
        r005_sunglasses=_bool(row.get("R005_Sunglasses")),
        r006_highcost_frames=_bool(row.get("R006_HighCost_Frames")),
        r007_highcost_lenses=_bool(row.get("R007_HighCost_Lenses")),
        r008_highcost_materials=_bool(row.get("R008_HighCost_Materials")),
        r009_high_billed_ratio=_bool(row.get("R009_High_Billed_Ratio")),
        r010_high_units=_bool(row.get("R010_High_Units")),
        r011_young_member=_bool(row.get("R011_Young_Member")),
        rule_flag_count=_int(row.get("Rule_Flag_Count")),
        rule_score_total=_float(row.get("Rule_Score_Total")),
        rule_narrative=_str(row.get("Rule_Narrative")),
        z_allowed_amount=_float(row.get("Z_AllowedAmount")),
        z_units=_float(row.get("Z_Units")),
        z_billed_to_allowed=_float(row.get("Z_BilledToAllowed")),
        claim_stat_score=_float(row.get("Claim_Stat_Score")),
        provider_stat_score=_float(row.get("Provider_Stat_Score")),
        stat_narrative=_str(row.get("Stat_Narrative")),
        if_score=_float(row.get("IF_Score")),
        if_score_norm=_float(row.get("IF_Score_Norm")),
        pca_recon_error=_float(row.get("PCA_Recon_Error")),
        pca_score_norm=_float(row.get("PCA_Score_Norm")),
        ml_anomaly_score=_float(row.get("ML_Anomaly_Score")),
        ml_anomaly_flag=_bool(row.get("ML_Anomaly_Flag")),
        ml_anomaly_narrative=_str(row.get("ML_Anomaly_Narrative")),
        ml_flag=_bool(row.get("ML_Flag")),
        rule_score_norm=_float(row.get("Rule_Score_Norm")),
        claim_stat_score_norm=_float(row.get("Claim_Stat_Score_Norm")),
        provider_stat_score_norm=_float(row.get("Provider_Stat_Score_Norm")),
        ml_anomaly_score_norm=_float(row.get("ML_Anomaly_Score_Norm")),
        final_combined_score=_float(row.get("Final_Combined_Score")),
        final_risk_level=_str(row.get("Final_Risk_Level")),
        final_fraud_type=_str(row.get("Final_Fraud_Type")),
        final_fraud_reason=_str(row.get("Final_Fraud_Reason")),
        final_narrative=_str(row.get("Final_Narrative")),
        ai_summary=_str(row.get("ai_summary")),
        ai_summary_generated=_bool(row.get("ai_summary_generated")),
        cluster_id=_str(row.get("cluster_id", row.get("ClusterId", "CL-00"))),
        similar_claim_ids=_str(row.get("Similar_Claim_Ids", "[]")),
        status="Flagged" if _str(row.get("Final_Risk_Level")) in ["High", "Critical"] else "Pending",
    )


def _provider_gold_payload(row: pd.Series) -> dict:
    return {
        "id": _str(row.get("id")),
        "raw_provider_id": _str(row.get("raw_provider_id")),
        "name": _str(row.get("name")),
        "specialty": _str(row.get("specialty")),
        "city": _str(row.get("city")),
        "state": _str(row.get("state")),
        "total_claims": _int(row.get("total_claims")),
        "total_allowed": _float(row.get("total_allowed")),
        "avg_allowed": _float(row.get("avg_allowed")),
        "avg_units": _float(row.get("avg_units")),
        "high_risk_claims": _int(row.get("high_risk_claims")),
        "high_risk_ratio": _float(row.get("high_risk_ratio")),
        "avg_final_score": _float(row.get("avg_final_score")),
        "avg_rule_score": _float(row.get("avg_rule_score")),
        "avg_stat_score": _float(row.get("avg_stat_score")),
        "avg_prov_stat_score": _float(row.get("avg_prov_stat_score")),
        "avg_ml_score": _float(row.get("avg_ml_score")),
        "provider_risk_score": _float(row.get("provider_risk_score")),
        "provider_risk_level": _str(row.get("provider_risk_level")),
        "provider_narrative": _str(row.get("provider_narrative")),
        "ai_pattern_deviation": _str(row.get("ai_pattern_deviation")),
        "ai_velocity_indicator": _str(row.get("ai_velocity_indicator")),
        "ai_recommendation": _str(row.get("ai_recommendation")),
    }


def _provider_name(row: pd.Series, provider_id: str) -> str:
    raw_provider_id = _str(row.get("ProviderId", provider_id))
    return _str(row.get("provider_name", "")) or provider_metadata(raw_provider_id)["name"]


def _format_member_id(raw: Any) -> str:
    raw_text = _str(raw)
    if not raw_text:
        return ""
    if raw_text.startswith("MEM-"):
        return raw_text
    return f"MEM-{raw_text[-7:]}"


def _str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)


def _int(value: Any) -> int:
    try:
        if value is None or pd.isna(value):
            return 0
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _float(value: Any) -> float:
    try:
        if value is None or pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _bool(value: Any) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    return bool(value)


if __name__ == "__main__":
    seed()
