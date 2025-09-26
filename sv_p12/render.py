"""Template-based renderers for production prompt strings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sv_p12.models import ScenePrompt
from sv_p12.templates import SFX_TPL, VIDEO_TPL, read


def _duration_string(value: float) -> str:
    text = f"{value:g}"
    if text == "0":
        return "0"
    return text


def render_video_prompt(scene: ScenePrompt) -> str:
    """Fill the video diffusion template with scene attributes.

    Supports both brace-format placeholders (e.g., {prompt}) and bracket labels
    (e.g., "[CONTENT]:") by detecting and applying the right substitution.
    """

    template = read(VIDEO_TPL)

    values = {
        "prompt": scene.prompt,
        "negative_prompt": scene.negative_prompt,
        "camera": scene.camera,
        "lighting": scene.lighting,
        "color": scene.color,
        "framing": scene.framing,
        "movement": scene.movement,
        "motion": scene.motion,
        "aspect_ratio": scene.aspect_ratio,
        "duration": _duration_string(scene.duration_sec),
        "transition_in": scene.transition_in,
        "transition_out": scene.transition_out,
        "safety": ", ".join(scene.safety_tags),
    }

    # If brace placeholders are present, use str.format
    if "{prompt}" in template or "{negative_prompt}" in template:
        try:
            return template.format(**values)
        except Exception:
            pass

    # Otherwise replace bracket labels inline
    out = template
    replace_map = {
        "[CONTENT]:": f"[CONTENT]: {values['prompt']}",
        "[NEGATIVE]:": f"[NEGATIVE]: {values['negative_prompt']}",
        "[CAMERA]:": f"[CAMERA]: {values['camera']}",
        "[LIGHTING]:": f"[LIGHTING]: {values['lighting']}",
        "[COLOR]:": f"[COLOR]: {values['color']}",
        "[FRAMING]:": f"[FRAMING]: {values['framing']}",
        "[MOVEMENT]:": f"[MOVEMENT]: {values['movement']}",
        "[MOTION]:": f"[MOTION]: {values['motion']}",
        "[ASPECT]:": f"[ASPECT]: {values['aspect_ratio']}",
        "[DURATION]:": f"[DURATION]: {values['duration']}s",
        "[TRANSITION_IN]:": f"[TRANSITION_IN]: {values['transition_in']}",
        "[TRANSITION_OUT]:": f"[TRANSITION_OUT]: {values['transition_out']}",
        "[SAFETY]:": f"[SAFETY]: {values['safety']}",
    }
    for k, v in replace_map.items():
        out = out.replace(k, v)
    return out


def render_sfx_prompt(scene: ScenePrompt) -> str:
    """Fill the sound design template with audio guidance.

    Supports both brace-format placeholders and bracket labels.
    """

    template = read(SFX_TPL)

    if "{audio}" in template:
        try:
            return template.format(
                audio=scene.audio,
                duration=_duration_string(scene.duration_sec),
                safety=", ".join(scene.safety_tags),
            )
        except Exception:
            pass

    out = template
    replace_map = {
        "[AUDIO]:": f"[AUDIO]: {scene.audio}",
        "[NEGATIVE]:": f"[NEGATIVE]: {scene.negative_prompt}",
        "[DURATION]:": f"[DURATION]: {_duration_string(scene.duration_sec)}s",
        "[TRANSITION_IN]:": f"[TRANSITION_IN]: {scene.transition_in}",
        "[TRANSITION_OUT]:": f"[TRANSITION_OUT]: {scene.transition_out}",
        "[SAFETY]:": f"[SAFETY]: {', '.join(scene.safety_tags)}",
    }
    for k, v in replace_map.items():
        out = out.replace(k, v)
    return out


__all__ = ["render_video_prompt", "render_sfx_prompt"]
