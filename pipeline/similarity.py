from __future__ import annotations

import json

import pandas as pd


def compute_similarity(df: pd.DataFrame) -> pd.DataFrame:
    """Attach similar claims placeholder.

    TODO: Implement cosine similarity or ANN retrieval after POC. The current
    POC intentionally skips the expensive pairwise cosine matrix.
    """
    out = df.copy()
    out["Similar_Claim_Ids"] = json.dumps([])
    return out

