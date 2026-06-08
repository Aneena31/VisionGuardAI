from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from db.models import Claim, ProviderGold
from db.seed import _claim_from_row, _provider_gold_payload
from pipeline import config, ml, stats
from pipeline.pipeline import run_batch


@dataclass
class HistoricalData:
    claims_df: pd.DataFrame
    provider_gold_df: pd.DataFrame
    artifacts: dict[str, Any]
    population_stats: dict[str, Any]
    claims: list[Claim]
    claims_by_id: dict[str, Claim]
    providers_by_id: dict[str, ProviderGold]
    source_mtime_ns: int


_cache: HistoricalData | None = None
_cache_lock = threading.Lock()


def get_historical_data(force_reload: bool = False) -> HistoricalData:
    t0 = time.perf_counter()
    source = config.DEFAULT_DATA_FILE_PATH
    if not source.exists():
        raise FileNotFoundError(f"Claims data source not found: {source}")

    source_mtime_ns = source.stat().st_mtime_ns
    with _cache_lock:
        if _cache and not force_reload and _cache.source_mtime_ns == source_mtime_ns:
            print(
                f"[VisionGuard] historical data cache hit claims={len(_cache.claims):,} "
                f"duration={time.perf_counter() - t0:.3f}s",
                flush=True,
            )
            return _cache
        print(
            f"[VisionGuard] historical data cache miss forceReload={force_reload} source={source}",
            flush=True,
        )
        return _load_historical_data(source, source_mtime_ns)


def set_historical_data(claims_df: pd.DataFrame, provider_gold_df: pd.DataFrame, artifacts: dict[str, Any]) -> HistoricalData:
    t0 = time.perf_counter()
    print(
        f"[VisionGuard] historical data cache update started claims={len(claims_df):,} providers={len(provider_gold_df):,}",
        flush=True,
    )
    source = config.DEFAULT_DATA_FILE_PATH
    source_mtime_ns = source.stat().st_mtime_ns if source.exists() else 0
    data = _build_historical_data(claims_df, provider_gold_df, artifacts, source_mtime_ns)
    with _cache_lock:
        global _cache
        _cache = data
    print(
        f"[VisionGuard] historical data cache update completed duration={time.perf_counter() - t0:.3f}s",
        flush=True,
    )
    return data


def load_artifacts_into_state(app: Any, artifacts_path: Path | None = None) -> None:
    data = get_historical_data()
    artifacts_path = artifacts_path or config.DEFAULT_ARTIFACTS_PATH
    ml.save_artifacts(
        data.artifacts["scaler"],
        data.artifacts["isolation_forest"],
        data.artifacts["pca"],
        data.artifacts["ml_features"],
        artifacts_path,
        data.artifacts["score_stats"],
    )
    app.state.artifacts = ml.load_artifacts(artifacts_path)
    app.state.population_stats = data.population_stats


def _load_historical_data(source: Path, source_mtime_ns: int) -> HistoricalData:
    t0 = time.perf_counter()
    print(f"[VisionGuard] historical pipeline started source={source}", flush=True)
    claims_df, provider_gold_df, artifacts = run_batch(str(source))
    print(
        f"[VisionGuard] historical pipeline completed claims={len(claims_df):,} providers={len(provider_gold_df):,} "
        f"duration={time.perf_counter() - t0:.3f}s",
        flush=True,
    )
    return _build_historical_data(claims_df, provider_gold_df, artifacts, source_mtime_ns)


def _build_historical_data(
    claims_df: pd.DataFrame,
    provider_gold_df: pd.DataFrame,
    artifacts: dict[str, Any],
    source_mtime_ns: int,
) -> HistoricalData:
    t0 = time.perf_counter()
    print(
        f"[VisionGuard] historical object build started claims={len(claims_df):,} providers={len(provider_gold_df):,}",
        flush=True,
    )
    claims = [_claim_from_row(row) for _, row in claims_df.iterrows()]
    providers = [ProviderGold(**_provider_gold_payload(row)) for _, row in provider_gold_df.iterrows()]
    data = HistoricalData(
        claims_df=claims_df,
        provider_gold_df=provider_gold_df,
        artifacts=artifacts,
        population_stats=stats.get_population_stats_from_frame(claims_df),
        claims=claims,
        claims_by_id={claim.id: claim for claim in claims},
        providers_by_id={provider.id: provider for provider in providers},
        source_mtime_ns=source_mtime_ns,
    )
    global _cache
    _cache = data
    print(
        f"[VisionGuard] historical object build completed claims={len(claims):,} providers={len(providers):,} "
        f"duration={time.perf_counter() - t0:.3f}s",
        flush=True,
    )
    return data
