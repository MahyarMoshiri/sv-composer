"""Expectation controller endpoint."""
from __future__ import annotations

from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from sv_api.utils import ok
from sv_control.expectation import (
    compute_expectation_trace,
    default_beats,
    metaphor_bank_sha,
)
from sv_sdk.loader import load_metaphor_bank

router = APIRouter(prefix="/control")
logger = structlog.get_logger(__name__)


class ExpectationRequest(BaseModel):
    active_metaphors: List[str] = Field(default_factory=list)
    poles: Dict[str, str] = Field(default_factory=dict)
    beats: Optional[List[str]] = None
    base: str = "linear"


@router.post("/expectation")
def expectation_endpoint(request: ExpectationRequest) -> Dict[str, object]:
    beats = request.beats if request.beats else default_beats()
    bank = load_metaphor_bank()
    trace = compute_expectation_trace(beats, request.active_metaphors, bank=bank, base=request.base)
    fire = trace["fired_step"]

    logger.info(
        "control.expectation.computed",
        **{"bible.version": bank.version},
        active_metaphors=request.active_metaphors,
        fire_beat_index=fire.get("beat_index"),
        metaphors_sha=metaphor_bank_sha(),
    )

    payload = {
        "beats": trace["beats"],
        "curve_before": trace["curve_before"],
        "curve_after": trace["curve_after"],
        "fire": fire,
        "active_metaphors": trace["active_metaphors"],
        "poles": request.poles,
    }
    return ok(payload)
