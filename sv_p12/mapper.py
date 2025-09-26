"""Mapping rules converting beat-level material into scene prompts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from sv_p12.infer import BeatMaterial
from sv_p12.models import BeatName, ScenePrompt
from sv_p12.safety import compile_negative_prompt


@dataclass
class SceneDraft:
    """Intermediate scene representation prior to optional enrichment."""

    scene: ScenePrompt
    beat_material: BeatMaterial
    bans: List[str]
    base_styles: Dict[str, str]
    prompt_seed: str
    expectation_delta: float


SCHEMA_PRIORITY = ["boundary", "container", "path", "link", "balance"]


def _primary_schema(schemas: Sequence[str]) -> str:
    lowered = [schema.lower() for schema in schemas]
    for schema in SCHEMA_PRIORITY:
        if schema in lowered:
            return schema
    return "boundary"


def _camera_for_schema(schema: str) -> Tuple[str, str]:
    mapping = {
        "boundary": (
            "35mm lens from doorway threshold",
            "slow push-in along the threshold axis",
        ),
        "container": (
            "35mm lens framing the enclosing space",
            "slow push-in to emphasize enclosure",
        ),
        "path": (
            "28mm lens tracking along leading lines",
            "steady dolly glide down the path",
        ),
        "link": (
            "50mm lens favouring paired subjects",
            "short rack focus between subjects",
        ),
        "balance": (
            "40mm lens with centered symmetry",
            "locked-off balanced hold",
        ),
    }
    return mapping.get(schema, mapping["boundary"])


def _framing(distance: str, schema: str) -> str:
    base_map = {
        "close": "close framing, intimate perspective",
        "medium": "medium framing anchoring the subject",
        "far": "wide framing to situate the subject",
    }
    base = base_map.get(distance.lower(), "medium framing anchoring the subject")
    if schema in {"boundary", "container"}:
        return f"{base} seen from the threshold"
    if schema == "path":
        return f"{base} aligned with the path direction"
    if schema == "link":
        return f"{base} connecting both subjects"
    if schema == "balance":
        return f"{base} weighted symmetrically"
    return base


def _lighting_for_metaphors(metaphors: Sequence[str], schema: str) -> str:
    lowered = [m.lower() for m in metaphors]
    if any("light_dark" in m for m in lowered):
        return "low-key contrast with soft rim light"
    if schema == "path" or any("journey" in m for m in lowered):
        return "directional guide lighting leading forward"
    if any("sleep_is_threshold" in m for m in lowered):
        return "muted pre-dawn glow at the edge of shadow"
    return "soft cinematic fill"


def _color_for_metaphors(metaphors: Sequence[str]) -> str:
    lowered = [m.lower() for m in metaphors]
    if any("light_dark" in m for m in lowered):
        return "muted cools with warm edge glow"
    if any("journey" in m for m in lowered):
        return "grounded earth tones with gradual gradient"
    if any("sleep_is_threshold" in m for m in lowered):
        return "hushed neutrals with gentle haze"
    return "balanced neutral palette"


def _audio_for_metaphors(metaphors: Sequence[str]) -> str:
    lowered = [m.lower() for m in metaphors]
    audio: List[str] = []
    if any("light_dark" in m for m in lowered):
        audio.append("room tone, soft hush")
    if any("journey" in m for m in lowered):
        audio.append("subtle footfalls, distant air movement")
    if any("sleep_is_threshold" in m for m in lowered):
        audio.append("slow breathing hush")
    if not audio:
        audio.append("ambient room tone")
    return "; ".join(dict.fromkeys(audio))


def _beat_motion(beat: BeatName, metaphors: Sequence[str]) -> Tuple[str, str]:
    lowered = [m.lower() for m in metaphors]
    motion = {
        BeatName.hook: "stillness holds under contained tension",
        BeatName.setup: "minimal gestures establish the space",
        BeatName.development: "deliberate subject action adds detail",
        BeatName.turn: "sudden kinetic shift marks the pivot",
        BeatName.reveal: "measured reveals guide the eye",
        BeatName.settle: "motion eases into still calm",
    }[beat]
    if beat == BeatName.turn and any("journey" in m for m in lowered):
        motion = "decisive stride crosses the threshold"
    if beat == BeatName.development and any("journey" in m for m in lowered):
        motion = "forward steps carry the subject along the path"
    camera_motion = "steady hold"
    if beat in {BeatName.hook, BeatName.setup}:
        camera_motion = "restrained drift"
    if beat == BeatName.development:
        camera_motion = "measured advance"
    if beat == BeatName.turn:
        camera_motion = "kinetic burst"
    if beat in {BeatName.reveal, BeatName.settle}:
        camera_motion = "calming ease"
    return camera_motion, motion


def _clean_text(text: str, bans: Sequence[str]) -> str:
    lowered_bans = {ban.lower() for ban in bans}
    words = text.split()
    filtered = [word for word in words if word.lower().strip(",.;:!?") not in lowered_bans]
    cleaned = " ".join(filtered).strip()
    return cleaned


def _scene_prompt(material: BeatMaterial, bans: Sequence[str]) -> str:
    base = material.final_text.strip()
    base = base.rstrip(".")
    base = _clean_text(base, bans)
    segments: List[str] = []
    if base:
        segments.append(base)
    if material.tokens_must:
        segments.append("Feature " + ", ".join(material.tokens_must) + " prominently")
    if material.context:
        segments.append(material.context)
    prompt = ". ".join(segment for segment in segments if segment)
    return prompt + ("." if prompt and not prompt.endswith(".") else "")


def create_scene_draft(
    *,
    material: BeatMaterial,
    scene_idx: int,
    scene_count: int,
    start_sec: float,
    duration_sec: float,
    aspect_ratio: str,
    global_scene_index: int,
    viewpoint_distance: str,
    seed: int | None,
    expectation_delta: float,
) -> SceneDraft:
    primary_schema = _primary_schema(material.schemas)
    camera, movement = _camera_for_schema(primary_schema)
    lighting = _lighting_for_metaphors(material.metaphors, primary_schema)
    color = _color_for_metaphors(material.metaphors)
    audio = _audio_for_metaphors(material.metaphors)
    camera_motion, subject_motion = _beat_motion(material.beat, material.metaphors)

    movement_desc = movement
    if material.beat == BeatName.turn:
        camera = "handheld 35mm lens catching the pivot"
        movement_desc = "urgent handheld pivot"
        camera_motion = "kinetic burst"
        subject_motion = "sudden subject shift reveals the change"

    framing = _framing(viewpoint_distance, primary_schema)

    negative_prompt, safety_tags = compile_negative_prompt(material.tokens_ban)
    negative_terms = [token.strip().lower() for token in negative_prompt.split(",") if token.strip()]

    prompt_seed = _scene_prompt(material, material.tokens_ban)
    notes: List[str] = [material.intent]
    if material.context:
        notes.append(material.context)
    if scene_count > 1:
        notes.append(f"Scene {scene_idx + 1} of {scene_count}")

    scene_seed = seed + global_scene_index if seed is not None else None

    scene = ScenePrompt(
        scene_id=f"p12-b{material.index}-s{scene_idx + 1}",
        beat=material.beat,
        start_sec=start_sec,
        duration_sec=duration_sec,
        prompt=prompt_seed,
        negative_prompt=negative_prompt,
        camera=camera,
        lighting=lighting,
        color=color,
        framing=framing,
        movement=camera_motion,
        motion=subject_motion,
        audio=audio,
        transition_in="cut",
        transition_out="cut",
        safety_tags=safety_tags,
        seed=scene_seed,
        aspect_ratio=aspect_ratio,
        notes=" | ".join(notes) if notes else None,
    )

    base_styles = {
        "camera": camera,
        "lighting": lighting,
        "color": color,
        "motion": subject_motion,
    }
    return SceneDraft(
        scene=scene,
        beat_material=material,
        bans=negative_terms,
        base_styles=base_styles,
        prompt_seed=prompt_seed,
        expectation_delta=expectation_delta,
    )


def apply_transitions(sequences: Sequence[List[SceneDraft]]) -> None:
    """Mutate scene transitions based on beat adjacency rules."""

    for idx, draft_list in enumerate(sequences):
        if not draft_list:
            continue
        next_list = sequences[idx + 1] if idx + 1 < len(sequences) else None
        last_scene = draft_list[-1].scene
        if next_list:
            next_beat = next_list[0].scene.beat
            if last_scene.beat == BeatName.setup and next_beat == BeatName.development:
                last_scene.transition_out = "dissolve"
            if last_scene.beat == BeatName.turn:
                last_scene.transition_out = "match-cut"


__all__ = ["SceneDraft", "create_scene_draft", "apply_transitions"]
