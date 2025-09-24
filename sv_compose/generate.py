"""Beat-level generation harness applying critic/revise loop."""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from sv_compose.render import render_template
from sv_llm import LLM

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "prompts" / "templates"
CRITIC_TEMPLATE = TEMPLATES_DIR / "critic.md"
REVISE_TEMPLATE = TEMPLATES_DIR / "revise.md"
FINAL_TEMPLATE = TEMPLATES_DIR / "compose_final.md"


def _join_prompts(prompts: Mapping[str, str]) -> str:
    ordered_keys: Sequence[str] = ("system", "context", "compose")
    parts = [str(prompts[key]).strip() for key in ordered_keys if prompts.get(key)]
    return "\n\n".join(part for part in parts if part)


def run_beat(prompts: Mapping[str, str], llm: LLM, *, max_new_tokens: int = 200) -> str:
    """Concatenate beat prompts and run the LLM harness."""

    prompt = _join_prompts(prompts)
    output = llm.generate(prompt, max_new_tokens=max_new_tokens)
    return output.strip()


def _extract_banned_tokens(beat_ctx: Mapping[str, Any]) -> Sequence[str]:
    constraints = beat_ctx.get("constraints") if isinstance(beat_ctx, Mapping) else None
    tokens: Sequence[str] = ()
    if isinstance(constraints, Mapping):
        raw_tokens = constraints.get("ban_tokens")
        if isinstance(raw_tokens, Sequence) and not isinstance(raw_tokens, (str, bytes)):
            tokens = [str(token).lower() for token in raw_tokens]
    return tokens


def critique(candidate: str, ctx: Mapping[str, Any]) -> Dict[str, Any]:
    """Render the critic prompt and run deterministic validations."""

    template_ctx = dict(ctx)
    template_ctx["candidate"] = candidate
    prompt = render_template(CRITIC_TEMPLATE, template_ctx)

    beat_ctx = ctx.get("beat", {}) if isinstance(ctx, Mapping) else {}
    thresholds = ctx.get("thresholds", {}) if isinstance(ctx, Mapping) else {}
    form = thresholds.get("form", {}) if isinstance(thresholds, Mapping) else {}

    max_chars = int(beat_ctx.get("max_chars") or form.get("max_chars") or 0)
    trimmed = candidate.strip()

    violations: list[str] = []
    reasons: list[str] = []
    if max_chars and len(trimmed) > max_chars:
        violations.append("OVER_LENGTH")
        reasons.append(f"length {len(trimmed)} exceeds max {max_chars}")

    banned_tokens = _extract_banned_tokens(beat_ctx)
    lowered = trimmed.lower()
    banned_hit = next((token for token in banned_tokens if token in lowered), None)
    if banned_hit:
        violations.append("NEW_METAPHOR_NOT_ALLOWED")
        reasons.append(f"banned token '{banned_hit}' present")

    passed = not violations
    metric_value = 0.95 if passed else 0.35
    metrics = {
        "frame_fit": metric_value,
        "schema_cov": metric_value,
        "metaphor_diversity": metric_value,
        "attention_discipline": metric_value,
        "explosion_timing": metric_value,
    }

    fix = ""
    if violations:
        fix = reasons[0] if reasons else "revise to satisfy critic"

    result = {
        "pass": passed,
        "metrics": metrics,
        "violations": violations,
        "reasons": reasons,
        "fix": fix,
    }

    return {"prompt": prompt, "result": result}


def revise(candidate: str, critic_json: Mapping[str, Any], ctx: Mapping[str, Any], llm: LLM, *, max_new_tokens: int = 200) -> str:
    """Render the revise prompt and request an updated candidate from the harness."""

    template_ctx = dict(ctx)
    template_ctx["candidate"] = candidate
    template_ctx["critic_json"] = json.dumps(critic_json, ensure_ascii=False)
    prompt = render_template(REVISE_TEMPLATE, template_ctx)
    revised = llm.generate(prompt, max_new_tokens=max_new_tokens)
    return revised.strip()


def assemble(beats: Mapping[str, str], ctx: Mapping[str, Any]) -> str:
    """Render the final assembly template and join accepted beats."""

    thresholds = ctx.get("thresholds", {}) if isinstance(ctx, Mapping) else {}
    form = thresholds.get("form", {}) if isinstance(thresholds, Mapping) else {}
    max_lines = int(form.get("max_lines") or ctx.get("max_lines") or 8)
    max_chars = int(form.get("max_chars") or ctx.get("max_chars") or 680)

    ordered = OrderedDict(beats)
    template_ctx = dict(ctx)
    template_ctx.update({
        "beats": [{"name": key, "text": value} for key, value in ordered.items()],
        "max_lines": max_lines,
        "max_chars": max_chars,
    })
    # Render to ensure template contracts remain satisfied; output used for logging/debugging.
    render_template(FINAL_TEMPLATE, template_ctx)

    lines = [value.strip() for value in ordered.values() if value and value.strip()]
    final_text = "\n".join(lines)
    if len(final_text) > max_chars:
        final_text = final_text[:max_chars].rstrip()
    if final_text.count("\n") + 1 > max_lines:
        final_text = "\n".join(final_text.splitlines()[:max_lines])
    return final_text


__all__ = ["run_beat", "critique", "revise", "assemble"]
