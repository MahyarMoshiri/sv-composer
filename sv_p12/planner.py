"""Planner assembling film plans from inferred beat material."""
from __future__ import annotations

import hashlib
from math import floor
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from sv_p12.infer import InferenceResult, hash_source
from sv_p12.mapper import SceneDraft, apply_transitions, create_scene_draft
from sv_p12.models import AllocationMode, BeatName, FilmPlan, SequencePlan, SinglePromptRequest

StyleCallback = Callable[[SceneDraft], Optional[Dict[str, str]]]


def _expectation_deltas(inference: InferenceResult) -> List[float]:
    deltas: List[float] = []
    for idx, material in enumerate(inference.beats):
        before = inference.curve_before[idx] if idx < len(inference.curve_before) else 0.0
        after = inference.curve_after[idx] if idx < len(inference.curve_after) else before
        delta = abs(after - before)
        if delta == 0.0 and material.beat == BeatName.turn:
            delta = 0.5
        deltas.append(delta)
    if all(delta == 0.0 for delta in deltas):
        return [2.0 if mat.beat == BeatName.turn else 1.0 for mat in inference.beats]
    return deltas


def _allocate_equal(scene_total: int, beats: Sequence[BeatName]) -> Dict[BeatName, int]:
    base = scene_total // len(beats)
    remainder = scene_total % len(beats)
    allocation = {beat: base for beat in beats}
    for index in range(remainder):
        allocation[beats[index]] += 1
    return allocation


def _allocate_weighted(scene_total: int, inference: InferenceResult) -> Dict[BeatName, int]:
    weights = _expectation_deltas(inference)
    total_weight = sum(weights)
    if total_weight <= 0:
        return _allocate_equal(scene_total, [material.beat for material in inference.beats])
    provisional: List[Tuple[BeatName, float, int, float]] = []
    allocated = 0
    for material, weight in zip(inference.beats, weights):
        raw = (weight / total_weight) * scene_total
        count = floor(raw)
        remainder = raw - count
        provisional.append((material.beat, raw, count, remainder))
        allocated += count
    remaining = scene_total - allocated
    provisional.sort(key=lambda item: item[3], reverse=True)
    idx = 0
    while remaining > 0 and provisional:
        beat, raw, count, remainder = provisional[idx % len(provisional)]
        provisional[idx % len(provisional)] = (beat, raw, count + 1, remainder)
        remaining -= 1
        idx += 1
    return {beat: count for beat, _, count, _ in provisional}


def _ensure_minimums(allocation: Dict[BeatName, int], beats: Sequence[BeatName], scene_total: int) -> Dict[BeatName, int]:
    alloc = dict(allocation)
    for beat in beats:
        alloc[beat] = max(1, alloc.get(beat, 0))
    total = sum(alloc.values())
    if total <= scene_total:
        return alloc
    # trim from beats with the largest allocations while keeping >=1
    sorted_beats = sorted(beats, key=lambda beat: alloc[beat], reverse=True)
    idx = 0
    while total > scene_total and idx < len(sorted_beats):
        beat = sorted_beats[idx]
        if alloc[beat] > 1:
            alloc[beat] -= 1
            total -= 1
            continue
        idx += 1
    return alloc


def _word_count(text: str) -> int:
    return len([token for token in text.strip().split() if token])


def _sanitize_style(text: str, bans: Sequence[str]) -> str:
    lowered = {ban.lower() for ban in bans}
    tokens = text.split()
    filtered = [token for token in tokens if token.lower().strip(",.;:!?""'()[]{}") not in lowered]
    return " ".join(filtered).strip()


def plan_film(
    request: SinglePromptRequest,
    inference: InferenceResult,
    *,
    style_callback: Optional[StyleCallback] = None,
) -> FilmPlan:
    """Assemble a FilmPlan from the inferred beat material."""

    scene_length = float(request.scene_length_sec)
    if scene_length <= 0:
        raise ValueError("scene_length_sec must be positive")
    if request.total_duration_sec <= 0:
        raise ValueError("total_duration_sec must be positive")

    scene_total = floor(request.total_duration_sec / scene_length)
    if scene_total <= 0:
        raise ValueError("total_duration_sec too small for requested scene length")
    if scene_total < len(inference.beats):
        raise ValueError("total_duration_sec does not allow at least one scene per beat")

    beats_order = [material.beat for material in inference.beats]
    if request.allocation_mode == AllocationMode.CurveWeighted:
        allocation = _allocate_weighted(scene_total, inference)
    else:
        allocation = _allocate_equal(scene_total, beats_order)
    allocation = _ensure_minimums(allocation, beats_order, scene_total)

    drafts_by_beat: List[List[SceneDraft]] = []
    current_time = 0.0
    global_scene_index = 0
    deltas = _expectation_deltas(inference)
    delta_map = {material.beat: deltas[idx] for idx, material in enumerate(inference.beats)}
    for material in inference.beats:
        count = allocation.get(material.beat, 0)
        beat_drafts: List[SceneDraft] = []
        for scene_idx in range(count):
            start = current_time + scene_idx * scene_length
            draft = create_scene_draft(
                material=material,
                scene_idx=scene_idx,
                scene_count=count,
                start_sec=start,
                duration_sec=scene_length,
                aspect_ratio=request.aspect_ratio,
                global_scene_index=global_scene_index,
                viewpoint_distance=inference.viewpoint_distance,
                seed=request.seed,
                expectation_delta=delta_map.get(material.beat, 0.0),
            )
            beat_drafts.append(draft)
            global_scene_index += 1
        drafts_by_beat.append(beat_drafts)
        current_time += count * scene_length

    apply_transitions(drafts_by_beat)

    style_warnings: List[str] = []
    if style_callback is not None:
        for beat_drafts in drafts_by_beat:
            for draft in beat_drafts:
                updates = style_callback(draft)
                if not updates:
                    continue
                for field in ("camera", "lighting", "color", "motion"):
                    value = updates.get(field)
                    if not value:
                        continue
                    sanitized = _sanitize_style(value, draft.bans)
                    if not sanitized or _word_count(sanitized) > 20:
                        style_warnings.append(f"Discarded {field} enrichment for {draft.scene.scene_id}")
                        sanitized = draft.base_styles[field]
                    setattr(draft.scene, field, sanitized)

    sequences: List[SequencePlan] = []
    for beat_drafts in drafts_by_beat:
        if not beat_drafts:
            continue
        material = beat_drafts[0].beat_material
        scenes = [draft.scene for draft in beat_drafts]
        sequences.append(SequencePlan(beat=material.beat, intent=material.intent, scenes=scenes))

    planned_duration = scene_length * sum(len(seq.scenes) for seq in sequences)

    warnings = inference.warnings + style_warnings
    provenance = {
        "source": "prompt",
        "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
        "frame_id": inference.frame_id,
        "beats": [material.beat.value for material in inference.beats],
        "used_generate": inference.used_generate,
        "source_sha256": hash_source(inference.source_payload),
        "allocation_mode": request.allocation_mode.value,
    }

    return FilmPlan(
        frame_id=inference.frame_id,
        total_duration_sec=planned_duration,
        scene_length_sec=scene_length,
        aspect_ratio=request.aspect_ratio,
        style_pack=request.style_pack,
        sequences=sequences,
        warnings=warnings,
        provenance=provenance,
    )


__all__ = ["plan_film", "StyleCallback"]
