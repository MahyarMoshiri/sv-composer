"""Deterministic evaluator for composed pieces."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from sv_control.attention import attention_weights
from sv_control.expectation import find_explosion_step
from sv_control.lexicon import match_lemmas
from sv_eval.framecheck import ActiveState, check_frame, extract_active_from_trace
from sv_sdk.models import FrameBank, FrameItem, MetaphorBank, MetaphorItem

MetricValues = Dict[str, float]
PenaltyEntry = Dict[str, Any]


def _coerce_sequence(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, (str, bytes))]
    if isinstance(value, tuple):
        return [str(item) for item in value if isinstance(item, (str, bytes))]
    if isinstance(value, set):
        return [str(item) for item in value if isinstance(item, (str, bytes))]
    if isinstance(value, str):
        return [value]
    return []


def _frame_bank(banks: Mapping[str, Any]) -> Optional[FrameBank]:
    frames = banks.get("frames") if isinstance(banks, Mapping) else None
    if isinstance(frames, FrameBank):
        return frames
    return None


def _metaphor_bank(banks: Mapping[str, Any]) -> Optional[MetaphorBank]:
    metaphors = banks.get("metaphors") if isinstance(banks, Mapping) else None
    if isinstance(metaphors, MetaphorBank):
        return metaphors
    return None


def _frame_by_id(frame_id: Optional[str], bank: Optional[FrameBank]) -> Optional[FrameItem]:
    if not frame_id or bank is None:
        return None
    for frame in bank.frames:
        if frame.id == frame_id:
            return frame
    return None


def _metaphor_map(bank: Optional[MetaphorBank]) -> Dict[str, MetaphorItem]:
    if bank is None:
        return {}
    return {metaphor.id: metaphor for metaphor in bank.metaphors}


def _augment_active_from_beats(trace: Mapping[str, Any], base: ActiveState) -> ActiveState:
    if not isinstance(trace, Mapping):
        return base
    beats = trace.get("beats")
    if isinstance(beats, Sequence):
        for entry in beats:
            if not isinstance(entry, Mapping):
                continue
            base.schemas.update(_coerce_sequence(entry.get("selected_schemas")))
            base.metaphors.update(_coerce_sequence(entry.get("selected_metaphors")))
            base.add_beat(entry.get("beat"))
    return base


def _active_state(trace: Mapping[str, Any]) -> ActiveState:
    state = extract_active_from_trace(trace)
    return _augment_active_from_beats(trace, state)


def _turn_index(beats: Sequence[Mapping[str, Any]]) -> Optional[int]:
    for index, beat in enumerate(beats):
        name = beat.get("beat") if isinstance(beat, Mapping) else None
        if isinstance(name, str) and name.lower() == "turn":
            return index
    if beats:
        return len(beats) // 2
    return None


def _range_from_thresholds(thresholds: Mapping[str, Any]) -> Tuple[float, float]:
    raw = thresholds.get("explosion_timing_range") if isinstance(thresholds, Mapping) else None
    if isinstance(raw, Sequence) and len(raw) == 2:
        low, high = raw
        try:
            return float(low), float(high)
        except (TypeError, ValueError):
            pass
    return 0.0, 1.0


def _score_explosion_timing(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 1.0
    if value <= 0.0:
        return 0.0
    if value < low and low > 0:
        return max(0.0, value / low)
    if value > high and high < 1.0:
        excess = value - high
        denom = max(1e-6, 1.0 - high)
        return max(0.0, 1.0 - excess / denom)
    return max(0.0, min(1.0, value))


def _metaphor_diversity(beats: Sequence[Mapping[str, Any]]) -> float:
    metaphors: List[str] = []
    for entry in beats:
        if not isinstance(entry, Mapping):
            continue
        metaphors.extend(_coerce_sequence(entry.get("selected_metaphors")))
    if not metaphors:
        return 0.0
    counts: Dict[str, int] = {}
    for item in metaphors:
        counts[item] = counts.get(item, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log(p, 2)
    diversity_max = math.log(len(counts), 2) if len(counts) > 1 else 1.0
    if diversity_max <= 0:
        return 0.0
    return max(0.0, min(1.0, entropy / diversity_max))


def _schema_coverage(piece: str, active: ActiveState, lang: str = "en") -> float:
    if not active.schemas:
        return 1.0
    matches = match_lemmas(piece, lang=lang)
    if not matches:
        return 0.0
    hit = sum(1 for schema in active.schemas if matches.get(schema, 0.0) > 0.0)
    return hit / max(len(active.schemas), 1)


def _attention_discipline(piece: str, lang: str = "en") -> float:
    peaks = attention_weights(piece, lang=lang, top_k=5)
    if not peaks:
        return 0.0
    weights = [max(0.0, float(peak.w)) for peak in peaks]
    total = sum(weights)
    if total <= 0.0:
        return 0.0
    focus = sum(weights[: min(3, len(weights))])
    return max(0.0, min(1.0, focus / total))


def _frame_fit_metric(frame: Optional[FrameItem], active: ActiveState) -> Tuple[float, Dict[str, Any]]:
    if frame is None:
        return 0.0, {"pass": False, "reasons": ["FRAME_NOT_FOUND"], "details": []}
    outcome = check_frame(active, frame)
    if outcome.get("pass", False):
        return 1.0, outcome
    reasons = outcome.get("reasons", [])
    penalty = 0.2 * len(reasons) if reasons else 0.4
    return max(0.0, 1.0 - penalty), outcome


def _resolved_weights(thresholds: Mapping[str, Any], frame_id: Optional[str], active: ActiveState) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    base = thresholds.get("weights") if isinstance(thresholds, Mapping) else {}
    if isinstance(base, Mapping):
        for key, value in base.items():
            try:
                weights[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    overrides = thresholds.get("overrides") if isinstance(thresholds, Mapping) else {}
    if isinstance(overrides, Mapping):
        frames = overrides.get("frames") if isinstance(overrides.get("frames"), Mapping) else {}
        if frame_id and isinstance(frames, Mapping):
            frame_override = frames.get(frame_id)
            if isinstance(frame_override, Mapping):
                custom = frame_override.get("weights")
                if isinstance(custom, Mapping):
                    for key, value in custom.items():
                        try:
                            weights[str(key)] = float(value)
                        except (TypeError, ValueError):
                            continue
        metaphors = overrides.get("metaphors") if isinstance(overrides.get("metaphors"), Mapping) else {}
        if isinstance(metaphors, Mapping):
            for metaphor_id in active.metaphors:
                meta_override = metaphors.get(metaphor_id)
                if isinstance(meta_override, Mapping):
                    custom = meta_override.get("weights")
                    if isinstance(custom, Mapping):
                        for key, value in custom.items():
                            try:
                                weights[str(key)] = float(value)
                            except (TypeError, ValueError):
                                continue
    return weights


def _resolved_penalties(thresholds: Mapping[str, Any], frame_id: Optional[str], active: ActiveState) -> Dict[str, float]:
    penalties: Dict[str, float] = {}
    base = thresholds.get("penalties") if isinstance(thresholds, Mapping) else {}
    if isinstance(base, Mapping):
        for key, value in base.items():
            try:
                penalties[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    overrides = thresholds.get("overrides") if isinstance(thresholds, Mapping) else {}
    if isinstance(overrides, Mapping):
        frames = overrides.get("frames") if isinstance(overrides.get("frames"), Mapping) else {}
        if frame_id and isinstance(frames, Mapping):
            frame_override = frames.get(frame_id)
            if isinstance(frame_override, Mapping):
                custom = frame_override.get("penalties")
                if isinstance(custom, Mapping):
                    for key, value in custom.items():
                        try:
                            penalties[str(key)] = float(value)
                        except (TypeError, ValueError):
                            continue
        metaphors = overrides.get("metaphors") if isinstance(overrides.get("metaphors"), Mapping) else {}
        if isinstance(metaphors, Mapping):
            for metaphor_id in active.metaphors:
                meta_override = metaphors.get(metaphor_id)
                if isinstance(meta_override, Mapping):
                    custom = meta_override.get("penalties")
                    if isinstance(custom, Mapping):
                        for key, value in custom.items():
                            try:
                                penalties[str(key)] = float(value)
                            except (TypeError, ValueError):
                                continue
    return penalties


def _apply_penalty(code: str, weight_map: Mapping[str, float], penalties: List[PenaltyEntry]) -> float:
    weight = float(weight_map.get(code, 0.0))
    if weight <= 0.0:
        return 0.0
    penalties.append({"code": code, "value": round(weight, 4)})
    return weight


def _in_range(value: float, bounds: Sequence[float]) -> bool:
    if not bounds or len(bounds) != 2:
        return True
    low, high = bounds
    return low <= value <= high


def _evaluate_rule(rule: str, context: Dict[str, Any]) -> bool:
    if not rule:
        return context.get("default", False)
    expression = rule.replace("AND", "and").replace("OR", "or").replace("NOT", "not")
    allowed = {"__builtins__": {}}
    allowed.update(context)
    try:
        return bool(eval(expression, allowed, {}))
    except Exception:
        return False


def _critical_enabled(code: str, config: Mapping[str, Any]) -> bool:
    flag = config.get(code)
    if isinstance(flag, bool):
        return flag
    return False


def _has_banned_pair(active: ActiveState, metaphors: Mapping[str, MetaphorItem]) -> Optional[str]:
    if not active.metaphors or not active.schemas:
        return None
    schema_set = set(active.schemas)
    for metaphor_id in active.metaphors:
        metaphor = metaphors.get(metaphor_id)
        if metaphor is None:
            continue
        banned = set(_coerce_sequence(metaphor.banned_with))
        if banned & schema_set:
            return metaphor_id
    return None


def evaluate(piece: str, trace: Mapping[str, Any] | None, thresholds: Mapping[str, Any], banks: Mapping[str, Any]) -> Dict[str, Any]:
    trace_data: Mapping[str, Any] = trace if isinstance(trace, Mapping) else {}
    piece_text = piece or ""
    stripped_piece = piece_text.strip()

    frame_bank = _frame_bank(banks)
    metaphor_bank = _metaphor_bank(banks)
    metaphor_lookup = _metaphor_map(metaphor_bank)

    active_state = _active_state(trace_data)
    frame_id = trace_data.get("frame_id") if isinstance(trace_data, Mapping) else None
    frame = _frame_by_id(frame_id, frame_bank)

    lang = "en"
    if isinstance(trace_data, Mapping):
        candidate_lang = trace_data.get("lang")
        if isinstance(candidate_lang, str) and candidate_lang:
            lang = candidate_lang
        else:
            meta = trace_data.get("meta")
            if isinstance(meta, Mapping):
                candidate_lang = meta.get("lang")
                if isinstance(candidate_lang, str) and candidate_lang:
                    lang = candidate_lang

    metrics: MetricValues = {}
    penalties_applied: List[PenaltyEntry] = []
    reasons: List[str] = []
    criticals: List[str] = []

    critical_config = thresholds.get("critical_violations") if isinstance(thresholds, Mapping) else {}
    if not isinstance(critical_config, Mapping):
        critical_config = {}

    penalties_weights = _resolved_penalties(thresholds, frame_id, active_state)
    if not stripped_piece and _critical_enabled("empty_output", critical_config):
        criticals.append("empty_output")

    trace_required = False
    if isinstance(thresholds, Mapping):
        form_section = thresholds.get("form", {})
        if isinstance(form_section, Mapping):
            trace_required = bool(form_section.get("trace_required", False))
    if trace_required and not trace_data:
        penalty = _apply_penalty("missing_trace", penalties_weights, penalties_applied)
        if penalty:
            reasons.append("missing trace")

    beats = trace_data.get("beats") if isinstance(trace_data, Mapping) else []
    beats_seq = [beat for beat in beats if isinstance(beat, Mapping)]
    turn_idx = _turn_index(beats_seq)

    low, high = _range_from_thresholds(thresholds)
    curve_after = trace_data.get("curve_after") if isinstance(trace_data, Mapping) else []
    curve_after_seq = [float(value) for value in curve_after] if isinstance(curve_after, Sequence) else []
    explosion_value = 0.0
    if turn_idx is not None and 0 <= turn_idx < len(curve_after_seq):
        explosion_value = float(curve_after_seq[turn_idx])
        if not _in_range(explosion_value, (low, high)):
            reasons.append(
                f"explosion value {explosion_value:.2f} outside range [{low:.2f}, {high:.2f}]"
            )
    metrics["explosion_timing"] = round(_score_explosion_timing(explosion_value, low, high), 4)

    frame_metric, frame_outcome = _frame_fit_metric(frame, active_state)
    metrics["frame_fit"] = round(frame_metric, 4)
    if not frame_outcome.get("pass", False):
        reasons.extend(frame_outcome.get("reasons", []))

    metrics["schema_cov"] = round(_schema_coverage(piece_text, active_state, lang=lang), 4)
    metrics["metaphor_diversity"] = round(_metaphor_diversity(beats_seq), 4)
    metrics["attention_discipline"] = round(_attention_discipline(piece_text, lang=lang), 4)

    if not frame_outcome.get("pass", False):
        penalty = _apply_penalty("frame_violation", penalties_weights, penalties_applied)
        if penalty:
            reasons.append("frame violation")

    form_limits = thresholds.get("form") if isinstance(thresholds, Mapping) else {}
    if not isinstance(form_limits, Mapping):
        form_limits = {}
    max_lines = int(form_limits.get("max_lines", 0)) if form_limits else 0
    max_chars = int(form_limits.get("max_chars", 0)) if form_limits else 0
    lines = [line for line in piece_text.splitlines() if line.strip()]
    over_length = False
    if max_lines and len(lines) > max_lines:
        over_length = True
    if max_chars and len(piece_text) > max_chars:
        over_length = True
    if over_length:
        penalty = _apply_penalty("over_length", penalties_weights, penalties_applied)
        if penalty:
            reasons.append("over length")

    banned_metaphor = _has_banned_pair(active_state, metaphor_lookup)
    if banned_metaphor:
        penalty = _apply_penalty("banned_pair", penalties_weights, penalties_applied)
        if penalty:
            reasons.append(f"banned pair via {banned_metaphor}")

    target = float(thresholds.get("explosion_timing_target", 0.85)) if isinstance(thresholds, Mapping) else 0.85
    if explosion_value and explosion_value < target:
        penalty = _apply_penalty("weak_turn", penalties_weights, penalties_applied)
        if penalty:
            reasons.append("weak explosion at turn")

    if not stripped_piece and "empty_output" not in criticals:
        reasons.append("empty output")

    explosion_target = {"threshold": target}
    if turn_idx is not None:
        explosion_target["min_index"] = turn_idx
        explosion_target["max_index"] = turn_idx
    fire = find_explosion_step(curve_after_seq, explosion_target)
    if turn_idx is not None and fire.get("beat_index") not in (turn_idx, -1):
        if _critical_enabled("explosion_outside_turn", critical_config):
            criticals.append("explosion_outside_turn")
            reasons.append("explosion fired outside turn")
    if _critical_enabled("disallowed_content", critical_config):
        flags = trace_data.get("flags") if isinstance(trace_data, Mapping) else {}
        if isinstance(flags, Mapping) and flags.get("disallowed_content"):
            criticals.append("disallowed_content")
            reasons.append("disallowed content flag")

    weights = _resolved_weights(thresholds, frame_id, active_state)
    score_pre_penalty = 0.0
    for key, weight in weights.items():
        score_pre_penalty += weight * metrics.get(key, 0.0)
    score_pre_penalty = round(score_pre_penalty, 4)

    total_penalty = sum(entry["value"] for entry in penalties_applied)
    total_penalty = min(total_penalty, 0.90)
    score_final = max(0.0, min(1.0, score_pre_penalty - total_penalty))
    score_final = round(score_final, 4)
    total_penalty = round(total_penalty, 4)

    floors_config = thresholds.get("metrics") if isinstance(thresholds, Mapping) else {}
    floors_ok = True
    if isinstance(floors_config, Mapping):
        for key, value in floors_config.items():
            if not key.endswith("_min"):
                continue
            metric_key = key[:-4]
            try:
                min_value = float(value)
            except (TypeError, ValueError):
                continue
            realized = metrics.get(metric_key, 0.0)
            if realized < min_value:
                floors_ok = False
                reasons.append(f"metric {metric_key} below min {min_value}")

    any_critical = bool(criticals)
    accept_threshold = float(thresholds.get("accept_threshold", 0.7)) if isinstance(thresholds, Mapping) else 0.7
    rule_context = {
        "score": score_pre_penalty,
        "total_penalty": total_penalty,
        "accept_threshold": accept_threshold,
        "floors_ok": floors_ok,
        "any_critical": any_critical,
        "in_range": lambda value, rng: _in_range(value, rng),
        "explosion_timing": explosion_value,
        "explosion_timing_range": (low, high),
    }
    acceptance_rule = str(thresholds.get("acceptance_rule", "")) if isinstance(thresholds, Mapping) else ""
    passed = _evaluate_rule(acceptance_rule, rule_context)

    metrics_out = {key: round(value, 4) for key, value in metrics.items()}

    result = {
        "pass": bool(passed),
        "score_pre_penalty": score_pre_penalty,
        "score_final": score_final,
        "total_penalty": total_penalty,
        "metrics": metrics_out,
        "penalties_applied": penalties_applied,
        "critical_violations": criticals,
        "reasons": reasons,
        "trace_echo": {
            "turn_index": turn_idx if turn_idx is not None else -1,
            "explosion_value": round(explosion_value, 4),
        },
    }
    return result


__all__ = ["evaluate"]
