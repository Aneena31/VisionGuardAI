# VisionGuard AI — Pipeline Reference

## Overview

This document is the canonical translation of the Jupyter notebook into production Python modules. Each notebook cell maps to a specific module and function. Codex should use this as the ground truth for implementing `pipeline/`.

---

## Notebook → Module Mapping

| Notebook Cell | Module | Function |
|---|---|---|
| Cell 1 — MLflow disable | `api/main.py` | startup event (ignore MLflow for FastAPI context) |
| Cell 1 — Load Excel | `pipeline/ingest.py` | `load_and_clean(file_path)` |
| Cell 3 — Basic Cleaning | `pipeline/ingest.py` | `load_and_clean(file_path)` |
| Cell 4 — Rule Engine | `pipeline/rules.py` | `apply_rules(df)` |
| Cell 5 — Rule Narratives | `pipeline/rules.py` | `generate_rule_narratives(df)` |
| Cell 6 — Rule Scoring | `pipeline/rules.py` | `apply_rule_scoring(df)` |
| Cell 7 — Statistical Outliers | `pipeline/stats.py` | `apply_statistical_outliers(df)` |
| Cell 8 — Unsupervised ML | `pipeline/ml.py` | `apply_unsupervised_ml(df)` |
| Cell 9 — Final Scoring | `pipeline/scoring.py` | `apply_final_scoring(df)` |
| Cell 10A — Similarity | `pipeline/similarity.py` | `compute_similarity(df)` |
| Cell 10B — Case Summary | `pipeline/ai_summary.py` | `generate_batch(df)` |
| Cell 11 — Provider Gold | `pipeline/aggregation.py` | `build_provider_gold(df)` |
| (New) AI Summary | `pipeline/ai_summary.py` | `generate_for_claim(claim_dict)` |

---

## `pipeline/ingest.py`

```python
import pandas as pd
import numpy as np

def load_and_clean(file_path: str) -> pd.DataFrame:
    """Load raw Excel, derive standard columns, assign row_id."""
    df = pd.read_excel(file_path)

    df["AmtAllowed"] = pd.to_numeric(df["AllowedAmount"], errors="coerce")
    df["Units"] = pd.to_numeric(df["UnitsUsed"], errors="coerce")
    df["PatientAge"] = pd.to_numeric(df["MemberAge"], errors="coerce")
    df["AmtCharged"] = pd.to_numeric(df["AmtCharged"], errors="coerce")

    df["BilledAmountToAllowedRatio"] = df["AmtCharged"] / df["AmtAllowed"].replace(0, np.nan)
    df["row_id"] = df.index + 1

    return df


def clean_single(claim_dict: dict) -> dict:
    """Normalize a single claim dict for pipeline input."""
    claim = claim_dict.copy()
    claim["AmtAllowed"] = float(claim.get("allowedAmount", 0) or 0)
    claim["Units"] = float(claim.get("units", 1) or 1)
    claim["PatientAge"] = int(claim.get("memberAge", 0) or 0)
    claim["AmtCharged"] = float(claim.get("amtCharged", 0) or 0)
    allowed = claim["AmtAllowed"] if claim["AmtAllowed"] != 0 else np.nan
    claim["BilledAmountToAllowedRatio"] = claim["AmtCharged"] / allowed if allowed else np.nan
    claim["row_id"] = 0
    claim["MemberAge"] = claim["PatientAge"]
    claim["ProcedureCode"] = claim.get("procedureCode", "")
    claim["ServiceCategoryName"] = claim.get("serviceCategoryName", "")
    claim["BenefitCategoryName"] = claim.get("benefitCategoryName", "")
    return claim
```

---

## `pipeline/rules.py`

Rules R001–R011 exactly as in the notebook. Key implementation notes:

**R001:** `df["ProcedureCode"].str.match(r"V27\d{2}")` — match V2700–V2799
**R002:** `df["ProcedureCode"].str.match(r"V2[1-3]\d")` — match V21X, V22X, V23X
**R003:** `df["ProcedureCode"].isin(["V2763", "V2764"])`
**R004:** `df["ProcedureCode"].isin(["V2020", "V2025"])`
**R005:** `df["ProcedureCode"].eq("V2744")`
**R006:** `ServiceCategoryName.str.contains("frame", case=False) & (AmtAllowed > 150)`
**R007:** `ServiceCategoryName.str.contains("lens", case=False) & (AmtAllowed > 200)`
**R008:** `BenefitCategoryName.str.contains("material", case=False) & (AmtAllowed > 250)`
**R009:** `BilledAmountToAllowedRatio > 2.0`
**R010:** `Units > 3`
**R011:** `(MemberAge < 18) & (AmtAllowed > 250) & BenefitCategoryName.contains("material", case=False)`

**Severity weights:**
```python
RULE_WEIGHTS = {
    "R001": 3, "R002": 2, "R003": 2, "R004": 1, "R005": 2,
    "R006": 3, "R007": 3, "R008": 4, "R009": 4, "R010": 2, "R011": 3
}
```
**Max possible Rule_Score_Total:** 3+2+2+1+2+3+3+4+4+2+3 = **29**

---

## `pipeline/stats.py`

```python
def compute_zscore(series: pd.Series) -> pd.Series:
    mean = series.mean()
    std = series.std()
    if std == 0:
        return (series - mean) * 0
    return (series - mean) / std
```

**Claim-level Z-scores:**
- `Z_AllowedAmount` = z-score of `AmtAllowed`
- `Z_Units` = z-score of `Units`
- `Z_BilledToAllowed` = z-score of `BilledAmountToAllowedRatio`

**Claim_Stat_Score (0–100):**
```
raw = abs(Z_AllowedAmount)*30 + abs(Z_Units)*20 + abs(Z_BilledToAllowed)*50
Claim_Stat_Score = 100 * raw / raw.max()
```

**Provider-level:** Group by `ProviderId`, compute mean of (`AmtAllowed`, `Units`, `BilledAmountToAllowedRatio`), then z-score those means across providers.

**Provider_Stat_Score:**
```
raw = abs(Z_Prov_Allowed)*40 + abs(Z_Prov_Units)*20 + abs(Z_Prov_Ratio)*40
Provider_Stat_Score = 100 * raw / raw.max()
```

**ML_Flag:** `(Claim_Stat_Score > 70) | (Provider_Stat_Score > 80)`

**Population stats for real-time use:**
```python
def get_population_stats(db) -> dict:
    """Compute mean/std for scaling single claims against historical population."""
    # Query DB for mean + std of AmtAllowed, Units, BilledAmountToAllowedRatio
    # Also get per-provider means for provider Z-score
    pass
```

---

## `pipeline/ml.py`

```python
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib

ML_FEATURES = [
    "AmtAllowed", "Units", "BilledAmountToAllowedRatio",
    "Rule_Flag_Count", "Claim_Stat_Score", "Provider_Stat_Score"
]

def apply_unsupervised_ml(df):
    X = df[ML_FEATURES].fillna(0).values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso = IsolationForest(n_estimators=200, contamination=0.03, random_state=42)
    iso.fit(X_scaled)
    df["IF_Score"] = -iso.score_samples(X_scaled)

    pca = PCA(n_components=0.95, svd_solver="full")
    X_pca = pca.fit_transform(X_scaled)
    X_rec = pca.inverse_transform(X_pca)
    df["PCA_Recon_Error"] = np.mean((X_scaled - X_rec) ** 2, axis=1)

    df["IF_Score_Norm"] = 100 * df["IF_Score"] / df["IF_Score"].max()
    df["PCA_Score_Norm"] = 100 * df["PCA_Recon_Error"] / df["PCA_Recon_Error"].max()
    df["ML_Anomaly_Score"] = df["IF_Score_Norm"] * 0.6 + df["PCA_Score_Norm"] * 0.4
    df["ML_Anomaly_Flag"] = df["ML_Anomaly_Score"] > 70

    return df, scaler, iso, pca, ML_FEATURES


def save_artifacts(scaler, iso, pca, ml_features, path):
    joblib.dump(scaler, f"{path}/scaler.pkl")
    joblib.dump(iso, f"{path}/isolation_forest.pkl")
    joblib.dump(pca, f"{path}/pca.pkl")
    import json
    with open(f"{path}/ml_features.json", "w") as f:
        json.dump(ml_features, f)


def load_artifacts(path):
    scaler = joblib.load(f"{path}/scaler.pkl")
    iso = joblib.load(f"{path}/isolation_forest.pkl")
    pca = joblib.load(f"{path}/pca.pkl")
    import json
    with open(f"{path}/ml_features.json") as f:
        ml_features = json.load(f)
    return scaler, iso, pca, ml_features


def score_single(claim_dict: dict, scaler, iso, pca, ml_features) -> dict:
    """Score a single claim using saved model artifacts."""
    row = [claim_dict.get(f, 0) or 0 for f in ml_features]
    X = np.array([row])
    X_scaled = scaler.transform(X)

    if_score = float(-iso.score_samples(X_scaled)[0])
    X_pca = pca.transform(X_scaled)
    X_rec = pca.inverse_transform(X_pca)
    pca_error = float(np.mean((X_scaled - X_rec) ** 2))

    return {"IF_Score": if_score, "PCA_Recon_Error": pca_error}
```

---

## `pipeline/scoring.py`

**Final scoring weights:**
```python
WEIGHTS = {
    "rule":     0.35,
    "stat":     0.20,
    "prov_stat":0.20,
    "ml":       0.25
}
```

**Risk level thresholds:**
```python
def risk_level(score: float) -> str:
    if score >= 80: return "Critical"
    if score >= 60: return "High"
    if score >= 40: return "Medium"
    return "Low"
```

**Fraud type logic:**
```python
def fraud_type(row) -> str:
    if row["ML_Anomaly_Score_Norm"] > 75:   return "ML Pattern Anomaly"
    if row["Provider_Stat_Score_Norm"] > 75: return "Provider Outlier Behavior"
    if row["Rule_Score_Norm"] > 75:          return "Rule-Based Upcoding / High-Cost"
    if row["Claim_Stat_Score_Norm"] > 75:    return "Claim-Level Outlier"
    return "No Significant Fraud Indicators"
```

---

## `pipeline/ai_summary.py`

```python
import openai
import json
import os

SYSTEM_PROMPT = """You are a healthcare fraud analyst AI assistant for an insurance SIU team.
Given structured claim analysis data, generate a concise professional investigation summary.
Respond ONLY with valid JSON. Keys: summary, riskReasoning, recommendation.
Each value must be a string under 100 words. Do not include any other text."""

def generate_for_claim(claim_data: dict) -> dict:
    """Call ChatOpenAI and return {summary, riskReasoning, recommendation}."""
    user_content = f"""
Claim Analysis:
- Procedure: {claim_data.get('ProcedureCode')} | Allowed: ${claim_data.get('AmtAllowed')}
- Member Age: {claim_data.get('MemberAge')} | Provider: {claim_data.get('ProviderId')}
- Rule Score: {claim_data.get('Rule_Score_Total', 0)}/29 | Rules triggered: {claim_data.get('Rule_Narrative', 'None')}
- Claim Z-Score: {claim_data.get('Z_AllowedAmount', 0):.2f} | Provider Z-Score: {claim_data.get('Z_Prov_Allowed', 0):.2f}
- Isolation Forest Score: {claim_data.get('IF_Score_Norm', 0):.1f}/100
- PCA Reconstruction Error Score: {claim_data.get('PCA_Score_Norm', 0):.1f}/100
- ML Narrative: {claim_data.get('ML_Anomaly_Narrative', 'None')}
- Final Score: {claim_data.get('Final_Combined_Score', 0):.1f}/100
- Risk Level: {claim_data.get('Final_Risk_Level')}
- Suspected Fraud Type: {claim_data.get('Final_Fraud_Type')}

Generate the investigation summary JSON.
"""
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)
    except Exception as e:
        # Fallback: template-based summary
        return {
            "summary": f"Risk level {claim_data.get('Final_Risk_Level')} detected. Score: {claim_data.get('Final_Combined_Score', 0):.0f}/100.",
            "riskReasoning": claim_data.get('Rule_Narrative', 'No specific rule triggers.'),
            "recommendation": "Review claim manually." if claim_data.get('Final_Risk_Level') in ['High', 'Critical'] else "No immediate action required."
        }


def generate_batch(df: pd.DataFrame, score_threshold: float = 40) -> pd.DataFrame:
    """Generate AI summaries for Medium+ risk claims only."""
    import time
    df = df.copy()
    summaries = []
    for _, row in df.iterrows():
        if row["Final_Combined_Score"] >= score_threshold:
            summary = generate_for_claim(row.to_dict())
            time.sleep(0.3)  # rate limiting
        else:
            summary = {
                "summary": "Low risk claim. No significant fraud indicators detected.",
                "riskReasoning": "All rule, statistical, and ML checks passed within normal thresholds.",
                "recommendation": "Auto-adjudicate."
            }
        summaries.append(json.dumps(summary))
    df["ai_summary"] = summaries
    return df
```

---

## `pipeline/pipeline.py` (Orchestrator)

```python
def run_batch(file_path: str):
    df = ingest.load_and_clean(file_path)
    df = rules.apply_rules(df)
    df = rules.generate_rule_narratives(df)
    df = rules.apply_rule_scoring(df)
    df = stats.apply_statistical_outliers(df)
    df, scaler, iso, pca, ml_features = ml.apply_unsupervised_ml(df)
    df = scoring.apply_final_scoring(df)
    df = similarity.compute_similarity(df)
    df = ai_summary.generate_batch(df)
    provider_gold = aggregation.build_provider_gold(df)
    artifacts = (scaler, iso, pca, ml_features)
    return df, provider_gold, artifacts


def run_single(claim_dict: dict, artifacts, population_stats: dict) -> dict:
    claim = ingest.clean_single(claim_dict)
    claim = rules.apply_rules_single(claim)
    claim = stats.score_single_claim(claim, population_stats)
    scores = ml.score_single(claim, *artifacts)
    claim.update(scores)
    claim = scoring.apply_final_scoring_single(claim)
    ai = ai_summary.generate_for_claim(claim)
    claim["ai_summary"] = ai
    return claim
```

---

## Tunable Thresholds (All in one place)

These are scattered across notebook cells. Centralize in `pipeline/config.py`:

```python
# pipeline/config.py

# Rule thresholds
THRESHOLD_HIGHCOST_FRAME = 150      # R006
THRESHOLD_HIGHCOST_LENS = 200       # R007
THRESHOLD_HIGHCOST_MATERIAL = 250   # R008
THRESHOLD_BILLED_RATIO = 2.0        # R009
THRESHOLD_HIGH_UNITS = 3            # R010
THRESHOLD_YOUNG_MEMBER_AGE = 18     # R011

# ML thresholds
IF_CONTAMINATION = 0.03
IF_N_ESTIMATORS = 200

# Statistical thresholds
ML_FLAG_CLAIM_SCORE_THRESHOLD = 70
ML_FLAG_PROVIDER_SCORE_THRESHOLD = 80
NARRATIVE_ZSCORE_THRESHOLD = 2.5

# Final scoring weights
WEIGHT_RULE = 0.35
WEIGHT_CLAIM_STAT = 0.20
WEIGHT_PROV_STAT = 0.20
WEIGHT_ML = 0.25

# Risk level thresholds
RISK_CRITICAL = 80
RISK_HIGH = 60
RISK_MEDIUM = 40

# AI summary
AI_SUMMARY_SCORE_THRESHOLD = 40   # only call OpenAI for claims above this
AI_RATE_LIMIT_SLEEP = 0.3         # seconds between API calls
```
