from __future__ import annotations

import time
from typing import Optional

import pandas as pd

from pipeline import aggregation, ai_summary, config, ingest, ml, rules, scoring, similarity, stats


def run_batch(file_path: Optional[str] = None):
    """Run the full historical batch pipeline."""
    source = file_path or str(config.DEFAULT_DATA_FILE_PATH)
    t0 = time.perf_counter()
    print(f"[VisionGuard] pipeline run_batch loading source={source}", flush=True)
    df = ingest.load_and_clean(source)
    print(
        f"[VisionGuard] pipeline load_and_clean completed rows={len(df):,} duration={time.perf_counter() - t0:.3f}s",
        flush=True,
    )
    return run_clean_batch(df)


def run_batch_dataframe(df: pd.DataFrame):
    """Run the full historical batch pipeline from an in-memory raw claims frame."""
    return run_clean_batch(ingest.clean_dataframe(df))


def run_clean_batch(df: pd.DataFrame):
    """Run the full historical batch pipeline from normalized claims."""
    total_t0 = time.perf_counter()
    print(f"[VisionGuard] pipeline scoring started rows={len(df):,}", flush=True)
    step_t0 = time.perf_counter()
    df = rules.apply_rules(df)
    df = rules.generate_rule_narratives(df)
    df = rules.apply_rule_scoring(df)
    print(f"[VisionGuard] pipeline rules completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    step_t0 = time.perf_counter()
    df = stats.apply_statistical_outliers(df)
    print(f"[VisionGuard] pipeline statistics completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    step_t0 = time.perf_counter()
    df, scaler, iso, pca, ml_features = ml.apply_unsupervised_ml(df)
    print(f"[VisionGuard] pipeline ml completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    step_t0 = time.perf_counter()
    df = scoring.apply_final_scoring(df)
    print(f"[VisionGuard] pipeline final scoring completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    step_t0 = time.perf_counter()
    df = similarity.compute_similarity(df)
    print(f"[VisionGuard] pipeline similarity completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    step_t0 = time.perf_counter()
    df = ai_summary.generate_batch(df)
    print(f"[VisionGuard] pipeline ai summaries completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    step_t0 = time.perf_counter()
    provider_gold = aggregation.build_provider_gold(df)
    print(f"[VisionGuard] pipeline provider aggregation completed duration={time.perf_counter() - step_t0:.3f}s", flush=True)
    artifacts = {
        "scaler": scaler,
        "isolation_forest": iso,
        "pca": pca,
        "ml_features": ml_features,
        "score_stats": {
            "if_score_max": float(df["IF_Score"].max() or 1),
            "pca_recon_error_max": float(df["PCA_Recon_Error"].max() or 1),
        },
    }
    print(f"[VisionGuard] pipeline scoring completed duration={time.perf_counter() - total_t0:.3f}s", flush=True)
    return df, provider_gold, artifacts


def run_single(claim_dict: dict, artifacts: dict, population_stats: dict) -> dict:
    """Run the single-claim scoring pipeline using cached artifacts."""
    claim = ingest.clean_single(claim_dict)
    claim = rules.apply_rules_single(claim)
    claim = stats.score_single_claim(claim, population_stats or {})
    claim.update(ml.score_single(claim, artifacts))
    claim = scoring.apply_final_scoring_single(claim)
    claim["ai_summary"] = ai_summary.generate_for_claim(claim)
    return claim
