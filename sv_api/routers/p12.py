"""Film plan endpoints for the P12 single-prompt module."""
from __future__ import annotations

import time
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException

from sv_p12.clients.openai_client import StyleEnrichSeed, enrich_style_with_llm
from sv_p12.config import load_p12_config
from sv_p12.infer import infer_plan_materials
from sv_p12.mapper import SceneDraft
from sv_p12.models import FilmPlan, SinglePromptRequest
from sv_p12.planner import StyleCallback, plan_film

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/p12", tags=["p12"])

_VALID_ASPECTS = {"16:9", "9:16", "1:1"}


@router.get("/ping")
def ping() -> dict[str, object]:
    """Simple health probe for the P12 module."""

    return {"ok": True, "module": "p12"}


def _validate_request(payload: SinglePromptRequest) -> None:
    length = float(payload.scene_length_sec)
    if length not in {5.0, 10.0}:
        raise HTTPException(status_code=400, detail="scene_length_sec must be 5 or 10")
    if payload.aspect_ratio not in _VALID_ASPECTS:
        raise HTTPException(status_code=400, detail="aspect_ratio must be one of 16:9, 9:16, 1:1")
    if payload.total_duration_sec <= 0:
        raise HTTPException(status_code=400, detail="total_duration_sec must be positive")


def _style_callback_factory(
    *,
    cfg,
    temperature: float,
    frame_id: str,
    viewpoint_distance: str,
    style_pack: Optional[str],
) -> StyleCallback:
    def _callback(draft: SceneDraft) -> Optional[dict[str, str]]:
        seed = StyleEnrichSeed(
            frame_id=frame_id,
            beat=draft.scene.beat,
            intent=draft.beat_material.intent,
            prompt_seed=draft.prompt_seed,
            camera=draft.scene.camera,
            lighting=draft.scene.lighting,
            color=draft.scene.color,
            motion=draft.scene.motion,
            bans=draft.bans,
            view_person="3rd",
            view_distance=viewpoint_distance,
            view_motive="",
            schemas=list(draft.beat_material.schemas),
            metaphors=list(draft.beat_material.metaphors),
            tokens_must=list(draft.beat_material.tokens_must),
            tokens_ban=list(draft.beat_material.tokens_ban),
            expectation_delta=draft.expectation_delta,
            tension_poles=[],
            duration_sec=draft.scene.duration_sec,
            aspect_ratio=draft.scene.aspect_ratio,
            style_pack=style_pack or "",
            prev_out_transition=draft.scene.transition_in,
            next_in_transition=draft.scene.transition_out,
        )
        return enrich_style_with_llm(seed, cfg, temperature=temperature)

    return _callback


@router.post("/filmplan", response_model=FilmPlan)
def create_film_plan(payload: SinglePromptRequest) -> FilmPlan:
    """Create a film production plan from a single textual prompt."""

    _validate_request(payload)

    started = time.perf_counter()
    inference = infer_plan_materials(payload)

    extra_warnings: list[str] = []
    style_callback: Optional[StyleCallback] = None
    enrich_active = bool(payload.llm_enrich)

    if payload.llm_enrich:
        cfg = load_p12_config()
        if cfg is None:
            extra_warnings.append("LLM enrichment requested but OPENAI_P12_API_KEY is not configured")
            enrich_active = False
        else:
            temperature = cfg.temperature if payload.temperature is None else max(0.0, float(payload.temperature))
            style_callback = _style_callback_factory(
                cfg=cfg,
                temperature=temperature,
                frame_id=inference.frame_id,
                viewpoint_distance=inference.viewpoint_distance,
                style_pack=payload.style_pack,
            )

    plan = plan_film(payload, inference, style_callback=style_callback)
    if extra_warnings:
        plan.warnings.extend(extra_warnings)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    provenance = plan.provenance
    logger.info(
        "p12.filmplan.generated",
        frame_id=plan.frame_id,
        beats=len(plan.sequences),
        scenes=sum(len(seq.scenes) for seq in plan.sequences),
        allocation_mode=payload.allocation_mode.value,
        llm_enrich=enrich_active,
        duration_ms=round(elapsed_ms, 2),
        source_sha256=provenance.get("source_sha256"),
    )

    return plan


__all__ = ["router"]
