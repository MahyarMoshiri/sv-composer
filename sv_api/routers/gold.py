"""Gold corpus API endpoints."""
from __future__ import annotations

from fastapi import APIRouter
import structlog

from sv_api.utils import ok
from sv_sdk.gold_loader import DEFAULT_GOLD_PATH, load_gold_jsonl
from sv_sdk.gold_stats import compute_gold_stats
from sv_sdk.loader import file_sha256, load_bible_version

router = APIRouter(prefix="/gold")
logger = structlog.get_logger(__name__)


@router.get("/stats")
def gold_stats() -> dict:
    """Return aggregate statistics for the gold corpus."""

    gold = load_gold_jsonl(DEFAULT_GOLD_PATH)
    stats = compute_gold_stats(gold)
    payload = {
        **stats,
        "sha256": file_sha256(DEFAULT_GOLD_PATH),
        "bible_version": load_bible_version(),
    }
    logger.info(
        "gold.stats.requested",
        **{"bible.version": payload["bible_version"]},
        items=payload["count"],
        sha256=payload["sha256"],
    )
    return ok(payload)
