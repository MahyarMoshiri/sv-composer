"""Optional OpenAI-backed style enrichment helpers for P12."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional

try:  # pragma: no cover - optional dependency
    from openai._exceptions import OpenAIError  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 - import guard when OpenAI SDK absent
    OpenAIError = Exception  # type: ignore[assignment]

from sv_p12.config import P12Config, get_p12_openai_client
from sv_p12.models import BeatName
from sv_p12.templates import style_enrich_templates


@dataclass
class StyleEnrichSeed:
    """Seed payload handed to the enrichment LLM."""

    frame_id: str
    beat: BeatName
    intent: str
    prompt_seed: str
    camera: str
    lighting: str
    color: str
    motion: str
    bans: List[str]
    view_person: str = "3rd"
    view_distance: str = ""
    view_motive: str = ""
    schemas: List[str] = field(default_factory=list)
    metaphors: List[str] = field(default_factory=list)
    tokens_must: List[str] = field(default_factory=list)
    tokens_ban: List[str] = field(default_factory=list)
    expectation_delta: float = 0.0
    tension_poles: List[str] = field(default_factory=list)
    duration_sec: float = 0.0
    aspect_ratio: str = "16:9"
    style_pack: Optional[str] = None
    prev_out_transition: str = ""
    next_in_transition: str = ""


@lru_cache(maxsize=1)
def _system_prompt() -> str:
    sys_t, _ = style_enrich_templates()
    return sys_t.strip()


@lru_cache(maxsize=1)
def _user_template() -> str:
    _, usr_t = style_enrich_templates()
    return usr_t


def _format_user_content(seed: StyleEnrichSeed) -> str:
    template = _user_template()
    replacements = {
        "{{scene_seed}}": seed.prompt_seed,
        "{{beat}}": seed.beat.value,
        "{{intent}}": seed.intent or "",
        "{{frame_id}}": seed.frame_id,
        "{{view_person}}": seed.view_person,
        "{{view_distance}}": seed.view_distance,
        "{{view_motive}}": seed.view_motive,
        "{{active_schemas_json}}": json.dumps(seed.schemas),
        "{{active_metaphors_json}}": json.dumps(seed.metaphors),
        "{{tokens_must_json}}": json.dumps(seed.tokens_must),
        "{{tokens_ban_json}}": json.dumps(seed.tokens_ban),
        "{{expectation_delta}}": f"{seed.expectation_delta:.4f}",
        "{{tension_poles_json}}": json.dumps(seed.tension_poles),
        "{{duration_sec}}": f"{seed.duration_sec:.2f}",
        "{{aspect_ratio}}": seed.aspect_ratio,
        "{{style_pack}}": seed.style_pack or "",
        "{{prev_out_transition}}": seed.prev_out_transition,
        "{{next_in_transition}}": seed.next_in_transition,
    }
    content = template
    for key, value in replacements.items():
        content = content.replace(key, value)
    return content


def _parse_json(content: str) -> Optional[Dict[str, str]]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    expected = {"camera", "lighting", "color", "motion"}
    if not isinstance(data, dict) or not expected.issubset(data.keys()):
        return None
    result: Dict[str, str] = {}
    for key in expected:
        value = data.get(key)
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        result[key] = text
    return result


def enrich_style_with_llm(
    seed: StyleEnrichSeed,
    cfg: P12Config,
    *,
    temperature: Optional[float] = None,
    timeout: int = 10,
) -> Optional[Dict[str, str]]:
    """Enrich stylistic fragments using the configured OpenAI client."""

    client = get_p12_openai_client(cfg, timeout=timeout)
    if client is None:
        return None

    temp = cfg.temperature if temperature is None else max(0.0, temperature)

    try:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": _format_user_content(seed)},
            ],
            temperature=temp,
            max_tokens=200,
        )
    except OpenAIError:
        return None

    choice = response.choices[0] if response.choices else None
    content = choice.message.content.strip() if choice and choice.message and choice.message.content else ""
    if not content:
        return None
    return _parse_json(content)


__all__ = ["StyleEnrichSeed", "enrich_style_with_llm"]
