"""Frame coherence evaluation endpoint."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from sv_api.utils import err, ok
from sv_eval.framecheck import (
    ActiveState,
    check_frame,
    extract_active_from_trace,
    normalize_active,
)
from sv_sdk.loader import FRAMES_PATH, file_sha256, load_frame_bank
from sv_sdk.models import FrameBank, FrameItem

router = APIRouter(prefix="/eval")
logger = structlog.get_logger(__name__)


class FrameCheckActive(BaseModel):
    schemas: list[str] = Field(default_factory=list)
    metaphors: list[str] = Field(default_factory=list)
    gates: list[str] = Field(default_factory=list)
    beats: list[str] = Field(default_factory=list)
    beat: Optional[str] = None
    viewpoint: Dict[str, Any] = Field(default_factory=dict)


class FrameCheckRequest(BaseModel):
    frame_id: str
    active: Optional[FrameCheckActive] = None
    trace: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _ensure_source(cls, values: "FrameCheckRequest") -> "FrameCheckRequest":
        if values.active is None and values.trace is None:
            raise ValueError("framecheck requires either active selections or a trace")
        return values


@lru_cache(maxsize=1)
def _frame_bank() -> FrameBank:
    return load_frame_bank()


@lru_cache(maxsize=1)
def _frame_index() -> Dict[str, FrameItem]:
    return {frame.id: frame for frame in _frame_bank().frames}


@lru_cache(maxsize=1)
def _frames_sha() -> str:
    return file_sha256(FRAMES_PATH)


@router.post("/framecheck")
def framecheck_endpoint(request: FrameCheckRequest) -> Dict[str, Any]:
    frame = _frame_index().get(request.frame_id)
    if frame is None:
        return JSONResponse(status_code=404, content=err([f"frame '{request.frame_id}' not found"]))

    active_state: Optional[ActiveState] = None

    if request.trace is not None:
        active_state = extract_active_from_trace(request.trace)

    if request.active is not None:
        direct_state = normalize_active(request.active.model_dump(mode="python"))
        if active_state is None:
            active_state = direct_state
        else:
            active_state.schemas.update(direct_state.schemas)
            active_state.metaphors.update(direct_state.metaphors)
            active_state.gates.update(direct_state.gates)
            active_state.beats.update(direct_state.beats)
            if direct_state.viewpoint:
                merged = dict(active_state.viewpoint)
                merged.update(direct_state.viewpoint)
                active_state.viewpoint = merged

    result = check_frame(active_state, frame)

    logger.info(
        "eval.framecheck.completed",
        **{"bible.version": _frame_bank().version},
        frame_id=frame.id,
        frames_sha=_frames_sha(),
        reasons=result.get("reasons", []),
    )

    return ok(result)
