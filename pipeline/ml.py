from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from pipeline import config


ML_FEATURES = [
    "AmtAllowed",
    "Units",
    "BilledAmountToAllowedRatio",
    "Rule_Flag_Count",
    "Claim_Stat_Score",
    "Provider_Stat_Score",
]


def apply_unsupervised_ml(df: pd.DataFrame):
    """Train unsupervised ML once during seed and score the batch."""
    out = df.copy()
    X = out[ML_FEATURES].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(
        n_estimators=config.IF_N_ESTIMATORS,
        contamination=config.IF_CONTAMINATION,
        random_state=config.IF_RANDOM_STATE,
    )
    iso.fit(X_scaled)
    out["IF_Score"] = -iso.score_samples(X_scaled)

    pca = PCA(n_components=config.PCA_VARIANCE_RETAINED, svd_solver="full")
    X_pca = pca.fit_transform(X_scaled)
    X_rec = pca.inverse_transform(X_pca)
    out["PCA_Recon_Error"] = np.mean((X_scaled - X_rec) ** 2, axis=1)

    if_max = out["IF_Score"].max() or 1
    pca_max = out["PCA_Recon_Error"].max() or 1
    out["IF_Score_Norm"] = (100 * out["IF_Score"] / if_max).clip(0, 100)
    out["PCA_Score_Norm"] = (100 * out["PCA_Recon_Error"] / pca_max).clip(0, 100)
    out["ML_Anomaly_Score"] = out["IF_Score_Norm"] * 0.6 + out["PCA_Score_Norm"] * 0.4
    out["ML_Anomaly_Score_Norm"] = out["ML_Anomaly_Score"]
    out["ML_Anomaly_Flag"] = out["ML_Anomaly_Score"] > config.ML_ANOMALY_FLAG_THRESHOLD
    out["ML_Anomaly_Narrative"] = out.apply(_ml_narrative, axis=1)
    return out, scaler, iso, pca, ML_FEATURES


def save_artifacts(scaler, iso, pca, ml_features, path: Union[str, Path], score_stats: Optional[dict] = None):
    """Persist ML artifacts for API startup reuse."""
    artifact_path = Path(path)
    artifact_path.mkdir(parents=True, exist_ok=True)
    joblib.dump(scaler, artifact_path / "scaler.pkl")
    joblib.dump(iso, artifact_path / "isolation_forest.pkl")
    joblib.dump(pca, artifact_path / "pca.pkl")
    with open(artifact_path / "ml_features.json", "w", encoding="utf-8") as handle:
        json.dump(ml_features, handle)
    with open(artifact_path / "ml_score_stats.json", "w", encoding="utf-8") as handle:
        json.dump(score_stats or {}, handle)


def load_artifacts(path: Union[str, Path]) -> dict:
    """Load saved artifacts without retraining."""
    artifact_path = Path(path)
    with open(artifact_path / "ml_features.json", encoding="utf-8") as handle:
        ml_features = json.load(handle)
    score_stats_path = artifact_path / "ml_score_stats.json"
    score_stats = {}
    if score_stats_path.exists():
        with open(score_stats_path, encoding="utf-8") as handle:
            score_stats = json.load(handle)
    return {
        "scaler": joblib.load(artifact_path / "scaler.pkl"),
        "isolation_forest": joblib.load(artifact_path / "isolation_forest.pkl"),
        "pca": joblib.load(artifact_path / "pca.pkl"),
        "ml_features": ml_features,
        "score_stats": score_stats,
    }


def score_single(claim_dict: dict, artifacts: Union[dict, tuple]) -> dict:
    """Score a single claim using cached ML artifacts."""
    if isinstance(artifacts, tuple):
        scaler, iso, pca, ml_features = artifacts[:4]
        score_stats = {}
    else:
        scaler = artifacts["scaler"]
        iso = artifacts["isolation_forest"]
        pca = artifacts["pca"]
        ml_features = artifacts["ml_features"]
        score_stats = artifacts.get("score_stats", {})

    row = [claim_dict.get(feature, 0) or 0 for feature in ml_features]
    X = np.array([row])
    X_scaled = scaler.transform(X)
    if_score = float(-iso.score_samples(X_scaled)[0])
    X_pca = pca.transform(X_scaled)
    X_rec = pca.inverse_transform(X_pca)
    pca_error = float(np.mean((X_scaled - X_rec) ** 2))

    if_max = float(score_stats.get("if_score_max") or if_score or 1)
    pca_max = float(score_stats.get("pca_recon_error_max") or pca_error or 1)
    if_norm = float(np.clip(100 * if_score / if_max, 0, 100))
    pca_norm = float(np.clip(100 * pca_error / pca_max, 0, 100))
    ml_score = if_norm * 0.6 + pca_norm * 0.4
    result = {
        "IF_Score": if_score,
        "IF_Score_Norm": if_norm,
        "PCA_Recon_Error": pca_error,
        "PCA_Score_Norm": pca_norm,
        "ML_Anomaly_Score": ml_score,
        "ML_Anomaly_Score_Norm": ml_score,
        "ML_Anomaly_Flag": ml_score > config.ML_ANOMALY_FLAG_THRESHOLD,
    }
    result["ML_Anomaly_Narrative"] = _ml_narrative(pd.Series({**claim_dict, **result}))
    return result


def _ml_narrative(row: pd.Series) -> str:
    if_score = float(row.get("IF_Score_Norm", 0) or 0)
    pca_score = float(row.get("PCA_Score_Norm", 0) or 0)
    ml_score = float(row.get("ML_Anomaly_Score_Norm", row.get("ML_Anomaly_Score", 0)) or 0)
    allowed = float(row.get("AmtAllowed", 0) or 0)
    charged = float(row.get("AmtCharged", 0) or 0)
    ratio = float(row.get("BilledAmountToAllowedRatio", 0) or 0)
    procedure = row.get("ProcedureCode", "the submitted procedure")

    if ml_score > config.ML_ANOMALY_FLAG_THRESHOLD:
        strongest_signal = "payment amount pattern" if if_score >= pca_score else "claim feature reconstruction pattern"
        return (
            f"ML anomaly checks are elevated for {procedure}: the combined ML score is {ml_score:.1f}/100, "
            f"with Isolation Forest at {if_score:.1f}/100 and PCA reconstruction at {pca_score:.1f}/100. "
            f"The strongest signal is the {strongest_signal}. The claim allowed amount is ${allowed:,.2f} "
            f"against ${charged:,.2f} billed, a billed-to-allowed ratio of {ratio:.2f}, which makes the claim "
            "worth manual review against comparable historical claims."
        )

    return (
        f"ML anomaly checks are not elevated for {procedure}: the combined ML score is {ml_score:.1f}/100, "
        f"with Isolation Forest at {if_score:.1f}/100 and PCA reconstruction at {pca_score:.1f}/100. "
        f"The allowed amount is ${allowed:,.2f} and the billed-to-allowed ratio is {ratio:.2f}, which remains "
        "within the model's expected historical pattern."
    )

