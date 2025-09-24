"""Control endpoints for viewpoint inference and attention peaks."""
from __future__ import annotations

from functools import lru_cache

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from sv_api.utils import ok
from sv_control.attention import attention_weights
from sv_control.viewpoint import ViewHint, infer_viewpoint
from sv_sdk.loader import load_schema_bank


router = APIRouter(prefix="/control")
logger = structlog.get_logger(__name__)


class ViewpointRequest(BaseModel):
    prompt: str
    frame_id: str | None = None
    lang: str = "en"


class AttentionRequest(BaseModel):
    text: str
    lang: str = "en"
    top_k: int | None = None


@lru_cache(maxsize=1)
def _bible_version() -> str:
    return load_schema_bank().version


@router.post("/viewpoint")
def infer_viewpoint_endpoint(request: ViewpointRequest) -> dict:
    hint: ViewHint = infer_viewpoint(request.prompt, request.frame_id, request.lang)
    peaks = attention_weights(request.prompt, lang=request.lang)

    logger.info(
        "control.viewpoint.inferred",
        **{"bible.version": _bible_version()},
        frame_id=request.frame_id,
        lang=request.lang,
        hint=hint.model_dump(),
    )

    return ok(
        {
            "viewpoint": hint.model_dump(),
            "attention": [peak.model_dump() for peak in peaks],
        }
    )


@router.post("/attention")
def attention_endpoint(request: AttentionRequest) -> dict:
    top_k = request.top_k if request.top_k is not None else 5
    peaks = attention_weights(request.text, lang=request.lang, top_k=top_k)
    return ok({"attention": [peak.model_dump() for peak in peaks]})
