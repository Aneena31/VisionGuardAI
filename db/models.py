from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, Text

from db.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(String, primary_key=True)
    raw_claim_id = Column(Integer)
    row_id = Column(Integer)

    provider_id = Column(String, index=True)
    provider_name = Column(String)
    member_id = Column(String)
    member_age = Column(Integer)
    member_gender = Column(String)
    subscriber_id = Column(String)
    group_id = Column(String)

    procedure_code = Column(String, index=True)
    procedure_desc = Column(String)
    benefit_type = Column(String)
    service_category_name = Column(String)
    benefit_category_name = Column(String)
    service_date = Column(Date, index=True)
    service_year = Column(Integer)
    adjustment_version = Column(Integer)
    line_number = Column(Integer)

    amt_charged = Column(Float)
    amt_allowed = Column(Float)
    paid_amount = Column(Float)
    allowed_units = Column(Float)
    units_used = Column(Float)
    utilization_pct_amt = Column(Float)
    billed_amount_to_allowed_ratio = Column(Float)

    r001_material_upcoding = Column(Boolean, default=False)
    r002_material_upcoding_lens = Column(Boolean, default=False)
    r003_polycarb = Column(Boolean, default=False)
    r004_frame_upcoding = Column(Boolean, default=False)
    r005_sunglasses = Column(Boolean, default=False)
    r006_highcost_frames = Column(Boolean, default=False)
    r007_highcost_lenses = Column(Boolean, default=False)
    r008_highcost_materials = Column(Boolean, default=False)
    r009_high_billed_ratio = Column(Boolean, default=False)
    r010_high_units = Column(Boolean, default=False)
    r011_young_member = Column(Boolean, default=False)
    rule_flag_count = Column(Integer, default=0)
    rule_score_total = Column(Float, default=0)
    rule_narrative = Column(Text)

    z_allowed_amount = Column(Float)
    z_units = Column(Float)
    z_billed_to_allowed = Column(Float)
    claim_stat_score = Column(Float)
    provider_stat_score = Column(Float)
    stat_narrative = Column(Text)

    if_score = Column(Float)
    if_score_norm = Column(Float)
    pca_recon_error = Column(Float)
    pca_score_norm = Column(Float)
    ml_anomaly_score = Column(Float)
    ml_anomaly_flag = Column(Boolean, default=False)
    ml_anomaly_narrative = Column(Text)
    ml_flag = Column(Boolean, default=False)

    rule_score_norm = Column(Float)
    claim_stat_score_norm = Column(Float)
    provider_stat_score_norm = Column(Float)
    ml_anomaly_score_norm = Column(Float)
    final_combined_score = Column(Float, index=True)
    final_risk_level = Column(String, index=True)
    final_fraud_type = Column(String)
    final_fraud_reason = Column(Text)
    final_narrative = Column(Text)

    ai_summary = Column(Text)
    ai_summary_generated = Column(Boolean, default=False)
    cluster_id = Column(String)
    similar_claim_ids = Column(Text)

    status = Column(String, default="Pending", index=True)
    flagged_at = Column(DateTime)
    assigned_to = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProviderGold(Base):
    __tablename__ = "provider_gold"

    id = Column(String, primary_key=True)
    raw_provider_id = Column(String)
    name = Column(String)
    specialty = Column(String)
    city = Column(String)
    state = Column(String)

    total_claims = Column(Integer)
    total_allowed = Column(Float)
    avg_allowed = Column(Float)
    avg_units = Column(Float)
    high_risk_claims = Column(Integer)
    high_risk_ratio = Column(Float)

    avg_final_score = Column(Float)
    avg_rule_score = Column(Float)
    avg_stat_score = Column(Float)
    avg_prov_stat_score = Column(Float)
    avg_ml_score = Column(Float)

    provider_risk_score = Column(Float, index=True)
    provider_risk_level = Column(String, index=True)
    provider_narrative = Column(Text)

    ai_pattern_deviation = Column(Text)
    ai_velocity_indicator = Column(Text)
    ai_recommendation = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScoringJob(Base):
    __tablename__ = "scoring_jobs"

    id = Column(String, primary_key=True)
    status = Column(String, default="queued", index=True)
    source_type = Column(String)
    progress_percent = Column(Integer, default=0)
    active_stage = Column(String)
    claim_input_json = Column(Text)
    generated_claim_id = Column(String)
    result_json = Column(Text)
    error_message = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    assigned_queue = Column(String)
    assigned_at = Column(DateTime)
    assigned_to = Column(String)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True)
    type = Column(String)
    title = Column(String)
    message = Column(Text)
    related_claim_id = Column(String)
    related_provider_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(String, primary_key=True)
    status = Column(String)
    claims_processed = Column(Integer)
    claims_failed = Column(Integer)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    error_message = Column(Text)

