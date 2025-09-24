"""Composition planning and prompt packaging controller."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from sv_control.attention import attention_weights
from sv_control.expectation import compute_expectation_trace
from sv_control.viewpoint import infer_viewpoint
from sv_rag.index import RAGIndex
from sv_rag.select import select_active
from sv_sdk.loader import BEATS_CONFIG_PATH, load_beats_config, load_yaml
from sv_sdk.models import FrameItem

from .render import render_template
from .trace import ComposeTrace, ComposeTraceBeat

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "templates"
SYSTEM_TEMPLATE = TEMPLATES_DIR / "system.md"
CONTEXT_TEMPLATE = TEMPLATES_DIR / "retrieval_context.md"
BEAT_TEMPLATE = TEMPLATES_DIR / "compose_beat.md"
BEAT_PLAN_TEMPLATE = TEMPLATES_DIR / "beat_plan.md"
CRITIC_TEMPLATE = TEMPLATES_DIR / "critic.md"
REVISE_TEMPLATE = TEMPLATES_DIR / "revise.md"
FINAL_TEMPLATE = TEMPLATES_DIR / "compose_final.md"
CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
THRESHOLDS_PATH = CONFIG_DIR / "thresholds.yml"


@lru_cache(maxsize=1)
def _load_beats_dict() -> Dict[str, Any]:
    config = load_beats_config().model_dump(mode="python")
    return config


@lru_cache(maxsize=1)
def _load_thresholds() -> Dict[str, Any]:
    return load_yaml(THRESHOLDS_PATH)


def get_beats_config() -> Dict[str, Any]:
    return _load_beats_dict()


def get_thresholds_config() -> Dict[str, Any]:
    return _load_thresholds()


def _beats_by_name(config: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    beats = config.get("beats", [])
    mapping: Dict[str, Mapping[str, Any]] = {}
    for beat in beats:
        if isinstance(beat, Mapping):
            name = str(beat.get("name"))
            if name:
                mapping[name] = beat
    return mapping


def _fallback_plan(
    frame: FrameItem,
    active: Mapping[str, Any],
    beats_config: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    beats = beats_config.get("beats", [])
    schemas = list(active.get("schemas", []))
    metaphors = list(active.get("metaphors", []))
    plan: List[Dict[str, Any]] = []
    for beat in beats:
        if not isinstance(beat, Mapping):
            continue
        plan.append(
            {
                "name": beat.get("name"),
                "intent": beat.get("goal", ""),
                "focus": {
                    "schemas": schemas[:2],
                    "metaphors": metaphors[:2],
                },
                "expectation_target": float(beat.get("expectation_target", 0.0)),
            }
        )
    return plan


def plan_beats(
    frame: FrameItem,
    active: Mapping[str, Any],
    beats_cfg: Mapping[str, Any] | None,
    thresholds: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Render the beat plan template when available, otherwise return defaults."""

    beats_config = beats_cfg or _load_beats_dict()
    base_plan = _fallback_plan(frame, active, beats_config)
    if not BEAT_PLAN_TEMPLATE.exists():
        return base_plan

    context = {
        "frame": frame.model_dump(mode="python"),
        "active": active,
        "poles": active.get("poles", {}),
        "beats": beats_config.get("beats", []),
        "thresholds": thresholds,
    }

    try:
        rendered = render_template(BEAT_PLAN_TEMPLATE, context)
        payload = json.loads(rendered)
        beats = payload.get("beats")
        if not isinstance(beats, list):
            return base_plan
    except (ValueError, json.JSONDecodeError):
        return base_plan

    config_map = _beats_by_name(beats_config)
    hydrated: List[Dict[str, Any]] = []
    for entry in beats:
        if not isinstance(entry, Mapping):
            continue
        name = entry.get("name")
        if name not in config_map:
            continue
        expected_target = float(config_map[name].get("expectation_target", 0.0))
        intent = entry.get("intent") or config_map[name].get("goal", "")
        focus = entry.get("focus") if isinstance(entry.get("focus"), Mapping) else {}
        schemas = list(focus.get("schemas", [])) if isinstance(focus, Mapping) else []
        metaphors = list(focus.get("metaphors", [])) if isinstance(focus, Mapping) else []
        hydrated.append(
            {
                "name": name,
                "intent": intent,
                "focus": {
                    "schemas": schemas,
                    "metaphors": metaphors,
                },
                "expectation_target": expected_target,
            }
        )
    return hydrated or base_plan


def _plan_to_map(plan: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    mapping: Dict[str, Mapping[str, Any]] = {}
    for item in plan:
        name = item.get("name")
        if isinstance(name, str):
            mapping[name] = item
    return mapping


def _attention_summary(query: str, lang: str = "en") -> List[Dict[str, Any]]:
    peaks = attention_weights(query, lang=lang, top_k=5)
    return [{"token": peak.token, "w": peak.w} for peak in peaks]


def _monotonic_curve(values: Sequence[float]) -> List[float]:
    curve: List[float] = []
    last = 0.0
    for index, value in enumerate(values):
        current = max(last, float(value))
        if index == len(values) - 1:
            current = max(current, 1.0)
        curve.append(current)
        last = current
    return curve


def _must_tokens(
    plan_entry: Mapping[str, Any],
    lexicon: Mapping[str, Any],
) -> List[str]:
    focus = plan_entry.get("focus", {})
    tokens: List[str] = []
    if isinstance(focus, Mapping):
        schema_focus = focus.get("schemas", [])
        metaphor_focus = focus.get("metaphors", [])
        if isinstance(schema_focus, Iterable):
            for schema_id in schema_focus:
                lemma_list = (
                    lexicon.get("schemas", {}).get(schema_id, {}).get("en")
                    if isinstance(lexicon.get("schemas"), Mapping)
                    else None
                )
                if isinstance(lemma_list, list) and lemma_list:
                    tokens.append(str(lemma_list[0]))
        if isinstance(metaphor_focus, Iterable):
            for metaphor_id in metaphor_focus:
                lemma_list = (
                    lexicon.get("metaphors", {}).get(metaphor_id, {}).get("en")
                    if isinstance(lexicon.get("metaphors"), Mapping)
                    else None
                )
                if isinstance(lemma_list, list) and lemma_list:
                    tokens.append(str(lemma_list[0]))
    return tokens


def compose_beat(
    *,
    frame: FrameItem,
    active: Mapping[str, Any],
    beat_config: Mapping[str, Any],
    plan_entry: Mapping[str, Any],
    expectation_value: float,
    lexicon: Mapping[str, Any],
    common_context: Mapping[str, Any],
) -> Tuple[Dict[str, str], ComposeTraceBeat]:
    plan_focus = plan_entry.get("focus", {}) if isinstance(plan_entry, Mapping) else {}
    beat_payload = dict(beat_config)
    beat_payload["name"] = beat_config.get("name")
    beat_payload["goal"] = plan_entry.get("intent") or beat_config.get("goal", "")
    beat_payload["focus"] = plan_focus
    beat_payload["expectation_target"] = float(plan_entry.get("expectation_target", beat_config.get("expectation_target", 0.0)))

    must_tokens = _must_tokens(plan_entry, lexicon)
    ban_tokens = []
    constraints = beat_config.get("constraints") if isinstance(beat_config, Mapping) else {}
    if isinstance(constraints, Mapping):
        tokens = constraints.get("ban_tokens")
        if isinstance(tokens, Iterable) and not isinstance(tokens, (str, bytes)):
            ban_tokens = [str(token) for token in tokens]

    system_prompt = render_template(SYSTEM_TEMPLATE, dict(common_context))
    context_context = dict(common_context)
    context_context.update(
        {
            "expectation": expectation_value,
        }
    )
    context_prompt = render_template(CONTEXT_TEMPLATE, context_context)

    beat_context = {
        "frame": common_context.get("frame"),
        "active": active,
        "beat": beat_payload,
        "must_use": must_tokens,
        "ban_words": ban_tokens,
    }
    compose_prompt = render_template(BEAT_TEMPLATE, beat_context)

    prompts = {
        "system": system_prompt,
        "context": context_prompt,
        "compose": compose_prompt,
    }

    trace = ComposeTraceBeat(
        beat=beat_payload.get("name", ""),
        expectation_target=beat_payload["expectation_target"],
        selected_schemas=list(active.get("schemas", [])),
        selected_metaphors=list(active.get("metaphors", [])),
        poles=dict(active.get("poles", {})),
        tokens={"must": must_tokens, "ban": ban_tokens},
        prompts=prompts,
        plan={
            "intent": plan_entry.get("intent"),
            "focus": plan_focus,
        },
    )

    return prompts, trace


def compose_piece(
    *,
    frame_id: str,
    query: str,
    beats: Sequence[str],
    index: RAGIndex,
    top_schemas: int = 3,
    top_metaphors: int = 2,
    active: Mapping[str, Any] | None = None,
    plan: Sequence[Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    frame = index.frame(frame_id)
    if frame is None:
        raise ValueError(f"Unknown frame_id '{frame_id}'")

    thresholds = _load_thresholds()
    beats_config = _load_beats_dict()
    active_data: Mapping[str, Any]
    if active is None:
        active_data = select_active(
            frame_id,
            query,
            top_schemas=top_schemas,
            top_metaphors=top_metaphors,
            index=index,
        )
    else:
        active_data = active

    plan_data = plan or plan_beats(frame, active_data, beats_config, thresholds)
    plan_map = _plan_to_map(plan_data)
    beats_map = _beats_by_name(beats_config)

    ordered_beats = [beat for beat in beats if beat in beats_map]
    try:
        expectation = compute_expectation_trace(
            ordered_beats,
            active_data.get("metaphors", []),
            bank=index.metaphor_bank,
        )
    except ValueError:
        base_curve = _monotonic_curve(
            [
                beats_map.get(beat, {}).get("expectation_target", 0.0)
                for beat in ordered_beats
            ]
        )
        expectation = {
            "beats": ordered_beats,
            "curve_before": base_curve,
            "curve_after": base_curve,
        }
    expectation_map = {
        beat_name: expectation["curve_after"][idx]
        for idx, beat_name in enumerate(expectation.get("beats", ordered_beats))
    }

    viewpoint = infer_viewpoint(query, frame_id=frame_id, lang="en")
    attention = _attention_summary(query)

    frame_payload = frame.model_dump(mode="python")
    common_context = {
        "frame": frame_payload,
        "active": active_data,
        "viewpoint": viewpoint.model_dump(mode="python"),
        "attention": attention,
        "exemplars": active_data.get("exemplars", []),
    }

    beats_output: Dict[str, Dict[str, str]] = {}
    trace_beats: List[ComposeTraceBeat] = []

    for beat_name in ordered_beats:
        beat_config = beats_map[beat_name]
        plan_entry = plan_map.get(beat_name, {
            "name": beat_name,
            "intent": beat_config.get("goal", ""),
            "focus": {"schemas": [], "metaphors": []},
            "expectation_target": beat_config.get("expectation_target", 0.0),
        })
        expectation_value = expectation_map.get(beat_name, beat_config.get("expectation_target", 0.0))
        prompts, trace = compose_beat(
            frame=frame,
            active=active_data,
            beat_config=beat_config,
            plan_entry=plan_entry,
            expectation_value=expectation_value,
            lexicon=active_data.get("lexicon", {}),
            common_context=common_context,
        )
        beats_output[beat_name] = prompts
        trace_beats.append(trace)

    final_context = {
        "max_lines": beats_config.get("globals", {}).get("total_max_lines", 8),
        "max_chars": beats_config.get("globals", {}).get("total_max_chars", 680),
    }
    final_prompt = render_template(FINAL_TEMPLATE, final_context)

    critic_prompt = CRITIC_TEMPLATE.read_text(encoding="utf-8")
    revise_prompt = REVISE_TEMPLATE.read_text(encoding="utf-8")

    trace = ComposeTrace(
        frame_id=frame_id,
        beats=trace_beats,
        curve_before=expectation.get("curve_before", []),
        curve_after=expectation.get("curve_after", []),
    )

    return {
        "prompts": {
            "beats": beats_output,
            "critic": critic_prompt,
            "revise": revise_prompt,
            "final": final_prompt,
        },
        "trace": trace.as_dict(),
        "plan": plan_data,
        "active": active_data,
    }
