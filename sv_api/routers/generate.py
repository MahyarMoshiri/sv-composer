"""End-to-end generation controller joining compose, critic, and revise stages."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Mapping

import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from sv_api.rag import get_rag_index
from sv_api.utils import err, ok
from sv_compose.controller import compose_piece, get_beats_config, get_thresholds_config
from sv_compose.generate import assemble, critique, revise, run_beat
from sv_llm import LLM, get_llm
from sv_sdk.loader import (
    BLEND_RULES_PATH,
    FRAMES_PATH,
    METAPHORS_PATH,
    SCHEMA_PATH,
    file_sha256,
    load_bible_version,
)

logger = structlog.get_logger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    frame_id: str
    query: str
    beats: List[str] = Field(default_factory=list)
    llm: str | None = Field(default=None)


def _beats_by_name(config: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    mapping: Dict[str, Mapping[str, Any]] = {}
    beats = config.get("beats", []) if isinstance(config, Mapping) else []
    for entry in beats:
        if isinstance(entry, Mapping):
            name = entry.get("name")
            if isinstance(name, str) and name:
                mapping[name] = entry
    return mapping


@lru_cache(maxsize=1)
def _bible_meta() -> Dict[str, Any]:
    return {
        "bible.version": load_bible_version(),
        "bible.schemas_sha": file_sha256(SCHEMA_PATH),
        "bible.metaphors_sha": file_sha256(METAPHORS_PATH),
        "bible.frames_sha": file_sha256(FRAMES_PATH),
        "bible.blend_rules_sha": file_sha256(BLEND_RULES_PATH),
    }


def _load_llm(name: str | None) -> LLM:
    try:
        return get_llm(name)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(str(exc)) from exc


@router.post("/generate")
def generate(payload: GenerateRequest) -> Dict[str, Any]:
    if not payload.beats:
        return err(["beats list cannot be empty"])

    index = get_rag_index()
    frame = index.frame(payload.frame_id)
    if frame is None:
        return err([f"Unknown frame_id '{payload.frame_id}'"])

    try:
        llm = _load_llm(payload.llm)
    except ValueError as exc:
        return err([str(exc)])

    composition = compose_piece(
        frame_id=payload.frame_id,
        query=payload.query,
        beats=payload.beats,
        index=index,
    )

    thresholds = get_thresholds_config()
    beats_config = get_beats_config()
    beats_map = _beats_by_name(beats_config)

    frame_payload = frame.model_dump(mode="python")
    active = composition["active"]
    prompts = composition["prompts"].get("beats", {})

    trace = composition["trace"]
    trace_beats = trace.get("beats", []) if isinstance(trace, Mapping) else []
    trace_map = {beat_entry.get("beat"): beat_entry for beat_entry in trace_beats if isinstance(beat_entry, Mapping)}

    beat_outputs: Dict[str, Dict[str, Any]] = {}
    final_beats: Dict[str, str] = {}
    critique_summary: Dict[str, Any] = {}
    warnings: List[str] = []

    for beat_name in payload.beats:
        beat_prompts = prompts.get(beat_name)
        if not isinstance(beat_prompts, Mapping):
            warnings.append(f"Missing prompts for beat '{beat_name}'")
            continue

        candidate = run_beat(beat_prompts, llm)
        beat_ctx = {
            "frame": frame_payload,
            "active": active,
            "beat": beats_map.get(beat_name, {}),
            "thresholds": thresholds,
        }

        critic_initial = critique(candidate, beat_ctx)
        critic_result = critic_initial["result"]

        final_candidate = candidate
        revision_text: str | None = None
        critic_final = critic_result

        if not critic_result.get("pass", False):
            revision_text = revise(candidate, critic_result, beat_ctx, llm)
            if revision_text:
                final_candidate = revision_text
                critic_final = critique(final_candidate, beat_ctx)["result"]

        beat_outputs[beat_name] = {
            "candidate": candidate,
            "final": final_candidate,
        }
        if revision_text is not None:
            beat_outputs[beat_name]["revision"] = revision_text

        final_beats[beat_name] = final_candidate
        critique_summary[beat_name] = {
            "initial": {
                "pass": critic_result.get("pass", False),
                "violations": list(critic_result.get("violations", [])),
            },
            "final": {
                "pass": critic_final.get("pass", False),
                "violations": list(critic_final.get("violations", [])),
            },
        }

        trace_entry = trace_map.get(beat_name)
        if isinstance(trace_entry, Mapping):
            outputs = trace_entry.setdefault("outputs", {})
            outputs.update(
                {
                    "candidate": candidate,
                    "final": final_candidate,
                    "critique": {
                        "initial": critic_result,
                        "prompt": critic_initial["prompt"],
                        "final": critic_final,
                    },
                }
            )
            if revision_text is not None:
                outputs["revision"] = revision_text

    final_ctx = {
        "thresholds": thresholds,
        "frame": frame_payload,
        "active": active,
    }
    final_text = assemble(final_beats, final_ctx)

    enriched_trace = dict(trace)
    enriched_trace["critique"] = critique_summary

    logger.info(
        "generate.run.completed",
        frame_id=payload.frame_id,
        beats=len(payload.beats),
        harness=payload.llm,
        **_bible_meta(),
    )

    data = {
        "beats": beat_outputs,
        "final": final_text,
        "trace": enriched_trace,
    }
    envelope = ok(data)
    if warnings:
        envelope["warnings"] = warnings
    return envelope
