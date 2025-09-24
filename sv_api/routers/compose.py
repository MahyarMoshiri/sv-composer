"""Composition planning and prompt orchestration endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sv_api.rag import get_rag_index
from sv_api.utils import err, ok
from sv_compose.controller import (
    compose_piece,
    get_beats_config,
    get_thresholds_config,
    plan_beats,
)
from sv_rag.select import select_active

router = APIRouter()


def _top_counts(k: Optional[int]) -> tuple[int, int]:
    size = k or 8
    schemas = max(1, min(6, size))
    metaphors = max(1, min(4, max(1, size // 2)))
    return schemas, metaphors


class ComposePlanIn(BaseModel):
    frame_id: str
    query: str
    k: Optional[int] = None


@router.post("/compose/plan")
def compose_plan(payload: ComposePlanIn):
    index = get_rag_index()
    frame = index.frame(payload.frame_id)
    if frame is None:
        return err([f"Unknown frame_id '{payload.frame_id}'"])

    top_schemas, top_metaphors = _top_counts(payload.k)

    active = select_active(
        payload.frame_id,
        payload.query,
        top_schemas=top_schemas,
        top_metaphors=top_metaphors,
        index=index,
    )

    plan = plan_beats(
        frame,
        active,
        get_beats_config(),
        get_thresholds_config(),
    )

    data = {
        "plan": plan,
        "active": active,
        "warnings": [],
    }
    return ok(data)


class ComposeBeatIn(BaseModel):
    frame_id: str
    beat: str
    query: str
    active: Dict[str, Any]


@router.post("/compose/beat")
def compose_single_beat(payload: ComposeBeatIn):
    index = get_rag_index()
    frame = index.frame(payload.frame_id)
    if frame is None:
        return err([f"Unknown frame_id '{payload.frame_id}'"])

    plan = plan_beats(
        frame,
        payload.active,
        get_beats_config(),
        get_thresholds_config(),
    )

    result = compose_piece(
        frame_id=payload.frame_id,
        query=payload.query,
        beats=[payload.beat],
        index=index,
        active=payload.active,
        plan=plan,
    )

    prompts = result["prompts"]["beats"].get(payload.beat)
    trace_beats = result["trace"].get("beats", [])
    trace_beat = trace_beats[0] if trace_beats else {}

    return ok({"prompts": prompts, "trace_beat": trace_beat, "warnings": []})


class ComposeIn(BaseModel):
    frame_id: str
    query: str
    beats: Sequence[str] = Field(default_factory=list)
    k: Optional[int] = None
    active: Optional[Dict[str, Any]] = None


@router.post("/compose")
def compose(payload: ComposeIn):
    index = get_rag_index()
    frame = index.frame(payload.frame_id)
    if frame is None:
        return err([f"Unknown frame_id '{payload.frame_id}'"])

    top_schemas, top_metaphors = _top_counts(payload.k)

    result = compose_piece(
        frame_id=payload.frame_id,
        query=payload.query,
        beats=list(payload.beats),
        index=index,
        top_schemas=top_schemas,
        top_metaphors=top_metaphors,
        active=payload.active,
    )

    data = {
        "prompts": result["prompts"],
        "trace": result["trace"],
        "plan": result["plan"],
        "active": result["active"],
    }
    return ok(data)
