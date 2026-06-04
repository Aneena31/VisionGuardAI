from __future__ import annotations

import os

from pipeline import aggregation, ai_summary, config, ingest, ml, rules, scoring, similarity, stats


def run_batch(file_path: str | None = None):
    """Run the full historical batch pipeline."""
    source = file_path or os.getenv("DATA_FILE_PATH", str(config.DEFAULT_DATA_FILE_PATH))
    df = ingest.load_and_clean(source)
    df = rules.apply_rules(df)
    df = rules.generate_rule_narratives(df)
    df = rules.apply_rule_scoring(df)
    df = stats.apply_statistical_outliers(df)
    df, scaler, iso, pca, ml_features = ml.apply_unsupervised_ml(df)
    df = scoring.apply_final_scoring(df)
    df = similarity.compute_similarity(df)
    df = ai_summary.generate_batch(df)
    provider_gold = aggregation.build_provider_gold(df)
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
