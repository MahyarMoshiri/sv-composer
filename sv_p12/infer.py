"""Inference helpers for building film plans from a single prompt."""
from __future__ import annotations

import hashlib
import json
import string
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fastapi import HTTPException

from sv_api.rag import get_rag_index
from sv_api.routers.generate import GenerateRequest, generate as generate_route
from sv_p12.models import BeatName, SinglePromptRequest


DEFAULT_BEATS: List[BeatName] = [
    BeatName.hook,
    BeatName.setup,
    BeatName.development,
    BeatName.turn,
    BeatName.reveal,
    BeatName.settle,
]


@dataclass
class BeatMaterial:
    """Structured per-beat data used for scene planning."""

    beat: BeatName
    index: int
    intent: str
    final_text: str
    schemas: List[str]
    metaphors: List[str]
    tokens_must: List[str]
    tokens_ban: List[str]
    context: str


@dataclass
class InferenceResult:
    """Aggregate inference output for downstream planning."""

    frame_id: str
    beats: List[BeatMaterial]
    curve_before: List[float]
    curve_after: List[float]
    used_generate: bool
    warnings: List[str]
    source_payload: Dict[str, Any]
    viewpoint_distance: str


def _sanitise_beats(beats: Sequence[BeatName]) -> List[BeatName]:
    ordered: List[BeatName] = []
    seen: set[BeatName] = set()
    for beat in beats:
        if beat in seen:
            continue
        ordered.append(beat)
        seen.add(beat)
    return ordered or list(DEFAULT_BEATS)


def _infer_frame_id(prompt: str, explicit: Optional[str], warnings: List[str]) -> Tuple[str, str]:
    index = get_rag_index()
    frame_bank = index.frame_bank
    default_frame = frame_bank.frames[0].id if frame_bank.frames else "sleep_gate"
    default_distance = frame_bank.frames[0].viewpoint_defaults.distance if frame_bank.frames else "medium"

    if explicit:
        frame = index.frame(explicit)
        if frame is not None:
            return frame.id, frame.viewpoint_defaults.distance
        warnings.append(f"Unknown frame '{explicit}', falling back to retrieval match")

    hits = index.search(prompt, k=1, filter_kinds=["frame"])
    for hit in hits:
        frame = index.frame(hit.doc_id)
        if frame is not None:
            return frame.id, frame.viewpoint_defaults.distance

    warnings.append("No frame match found; using default frame")
    return default_frame, default_distance


def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        result = [str(item).strip() for item in value if str(item).strip()]
        return result
    return []


def _extract_tokens(entry: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    tokens = entry.get("tokens")
    if isinstance(tokens, Mapping):
        return _as_str_list(tokens.get("must")), _as_str_list(tokens.get("ban"))
    return [], []


def _beat_intent_fallback(beat: BeatName) -> str:
    intents = {
        BeatName.hook: "establish threshold tension",
        BeatName.setup: "establish stakes and setting",
        BeatName.development: "build movement and detail",
        BeatName.turn: "trigger the pivotal shift",
        BeatName.reveal: "show consequence with clarity",
        BeatName.settle: "land quietly and resolve tension",
    }
    return intents.get(beat, "shape the story beat")


def _call_generate(frame_id: str, prompt: str, beats: Sequence[BeatName]) -> Dict[str, Any]:
    request = GenerateRequest(frame_id=frame_id, query=prompt, beats=[beat.value for beat in beats], llm=None)
    envelope = generate_route(request)
    if not envelope.get("ok"):
        errors = envelope.get("errors") or ["generate call failed"]
        raise RuntimeError("; ".join(errors))
    return envelope.get("data", {})


def _material_from_generate(data: Mapping[str, Any], beats: Sequence[BeatName]) -> Tuple[List[BeatMaterial], List[float], List[float]]:
    beats_payload = data.get("beats") if isinstance(data, Mapping) else {}
    trace = data.get("trace") if isinstance(data, Mapping) else {}
    trace_beats = trace.get("beats") if isinstance(trace, Mapping) else []
    trace_map: Dict[str, Mapping[str, Any]] = {}
    if isinstance(trace_beats, Sequence):
        for entry in trace_beats:
            if isinstance(entry, Mapping):
                beat_name = entry.get("beat")
                if isinstance(beat_name, str):
                    trace_map[beat_name] = entry

    materials: List[BeatMaterial] = []
    for index, beat in enumerate(beats, start=1):
        beat_data = beats_payload.get(beat.value) if isinstance(beats_payload, Mapping) else None
        final_text = ""
        if isinstance(beat_data, Mapping):
            final_raw = beat_data.get("final")
            if isinstance(final_raw, str):
                final_text = final_raw.strip()
        trace_entry = trace_map.get(beat.value, {})
        plan = trace_entry.get("plan") if isinstance(trace_entry, Mapping) else {}
        intent = ""
        if isinstance(plan, Mapping):
            intent_raw = plan.get("intent")
            if isinstance(intent_raw, str):
                intent = intent_raw.strip()
        must_tokens, ban_tokens = _extract_tokens(trace_entry if isinstance(trace_entry, Mapping) else {})
        schemas = _as_str_list(trace_entry.get("selected_schemas")) if isinstance(trace_entry, Mapping) else []
        metaphors = _as_str_list(trace_entry.get("selected_metaphors")) if isinstance(trace_entry, Mapping) else []
        ctx = ""
        prompts = trace_entry.get("prompts") if isinstance(trace_entry, Mapping) else {}
        if isinstance(prompts, Mapping):
            context_raw = prompts.get("context")
            if isinstance(context_raw, str):
                ctx = context_raw.strip()
        materials.append(
            BeatMaterial(
                beat=beat,
                index=index,
                intent=intent or _beat_intent_fallback(beat),
                final_text=final_text or _beat_intent_fallback(beat),
                schemas=schemas,
                metaphors=metaphors,
                tokens_must=must_tokens,
                tokens_ban=ban_tokens,
                context=ctx,
            )
        )

    curve_before = trace.get("curve_before") if isinstance(trace, Mapping) else []
    curve_after = trace.get("curve_after") if isinstance(trace, Mapping) else []
    return materials, _as_curve(curve_before, len(beats)), _as_curve(curve_after, len(beats))


def _as_curve(raw: Any, expected: int) -> List[float]:
    if not isinstance(raw, Sequence):
        return [0.0] * expected
    result: List[float] = []
    for idx in range(expected):
        try:
            value = float(raw[idx])
        except (TypeError, ValueError, IndexError):
            value = 0.0
        result.append(value)
    return result


def _keywords(prompt: str) -> List[str]:
    tokens: List[str] = []
    for raw in prompt.lower().split():
        token = raw.strip(string.punctuation)
        if len(token) < 3:
            continue
        if token in {"the", "and", "for", "with", "from", "into", "over", "under", "that", "this", "there", "their", "before"}:
            continue
        tokens.append(token)
    return tokens


def _heuristic_schemas(tokens: Sequence[str], frame_allowed: Sequence[str]) -> List[str]:
    schemas: List[str] = []
    keyword_map = {
        "door": "boundary",
        "gate": "boundary",
        "frame": "boundary",
        "path": "path",
        "road": "path",
        "bridge": "link",
        "hand": "link",
        "balance": "balance",
        "threshold": "boundary",
        "sleep": "boundary",
        "dream": "boundary",
        "journey": "path",
        "river": "path",
    }
    for token in tokens:
        schema = keyword_map.get(token)
        if schema and schema not in schemas:
            schemas.append(schema)
    for schema in ("boundary", "path", "link"):
        if schema in frame_allowed and schema not in schemas:
            schemas.append(schema)
    if not schemas:
        schemas.append("boundary")
    return schemas


def _heuristic_metaphors(tokens: Sequence[str]) -> List[str]:
    metaphors: List[str] = []
    if any(token in {"light", "dark", "shadow"} for token in tokens):
        metaphors.append("light_dark")
    if "journey" in tokens or "path" in tokens:
        metaphors.append("life_is_journey")
    if "sleep" in tokens or "dream" in tokens:
        metaphors.append("sleep_is_threshold")
    return metaphors


def _heuristic_intent(beat: BeatName) -> str:
    return _beat_intent_fallback(beat)


def _distil_material(
    prompt: str,
    frame_id: str,
    beats: Sequence[BeatName],
    viewpoint_distance: str,
) -> Tuple[List[BeatMaterial], List[float], List[float]]:
    index = get_rag_index()
    frame = index.frame(frame_id)
    frame_allowed = frame.allowed_schemas if frame else []
    tokens = _keywords(prompt)
    schemas = _heuristic_schemas(tokens, frame_allowed)
    metaphors = _heuristic_metaphors(tokens)
    intent_map = {beat: _heuristic_intent(beat) for beat in beats}

    materials: List[BeatMaterial] = []
    for idx, beat in enumerate(beats, start=1):
        prefix = intent_map[beat]
        final_text = f"{prefix.capitalize()}: {prompt.strip()}"
        materials.append(
            BeatMaterial(
                beat=beat,
                index=idx,
                intent=prefix,
                final_text=final_text,
                schemas=list(schemas),
                metaphors=list(metaphors),
                tokens_must=tokens[:2],
                tokens_ban=[],
                context=f"Frame {frame_id} viewpoint {viewpoint_distance}",
            )
        )

    # fabricate a gentle expectation curve with a spike at the turn
    base_curve = [0.1, 0.2, 0.4, 0.65, 0.55, 0.35]
    before = base_curve[: len(beats)]
    after = [min(0.99, value + (0.2 if beat == BeatName.turn else 0.05)) for value, beat in zip(before, beats)]
    return materials, before, after


def infer_plan_materials(request: SinglePromptRequest) -> InferenceResult:
    """Infer frame, beats, and beat materials for a film plan."""

    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")

    warnings: List[str] = []
    beats = _sanitise_beats(request.beats or DEFAULT_BEATS)

    frame_id, viewpoint_distance = _infer_frame_id(request.prompt, request.frame_id, warnings)

    try:
        generate_data = _call_generate(frame_id, request.prompt, beats)
        materials, curve_before, curve_after = _material_from_generate(generate_data, beats)
        used_generate = True
        source_payload = {
            "frame_id": frame_id,
            "beats": [beat.value for beat in beats],
            "generate": generate_data,
        }
    except Exception as exc:  # noqa: BLE001 - fallback on any failure
        warnings.append(f"generate fallback engaged: {exc}")
        materials, curve_before, curve_after = _distil_material(request.prompt, frame_id, beats, viewpoint_distance)
        used_generate = False
        source_payload = {
            "frame_id": frame_id,
            "beats": [beat.value for beat in beats],
            "prompt": request.prompt,
        }

    return InferenceResult(
        frame_id=frame_id,
        beats=materials,
        curve_before=curve_before,
        curve_after=curve_after,
        used_generate=used_generate,
        warnings=warnings,
        source_payload=source_payload,
        viewpoint_distance=viewpoint_distance,
    )


def hash_source(payload: Mapping[str, Any]) -> str:
    """Stable SHA-256 of the source payload for provenance."""

    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


__all__ = ["BeatMaterial", "InferenceResult", "infer_plan_materials", "hash_source"]
