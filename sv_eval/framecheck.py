"""Frame coherence checking utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from sv_sdk.models import FrameItem

FRM_MISSING_REQUIRED_SCHEMA = "FRM_MISSING_REQUIRED_SCHEMA"
FRM_DISALLOWED_SCHEMA = "FRM_DISALLOWED_SCHEMA"
FRM_DISALLOWED_METAPHOR = "FRM_DISALLOWED_METAPHOR"
FRM_GATE_NOT_ALLOWED = "FRM_GATE_NOT_ALLOWED"
FRM_VIEWPOINT_MISMATCH = "FRM_VIEWPOINT_MISMATCH"
FRM_BEAT_AFFINITY_WEAK = "FRM_BEAT_AFFINITY_WEAK"

_ALLOWED_BEATS = {"hook", "setup", "development", "turn", "reveal", "settle"}
_BEAT_ALIASES = {"hook_out": "settle"}


@dataclass
class ActiveState:
    """Normalized view of active selections for coherence checking."""

    schemas: Set[str] = field(default_factory=set)
    metaphors: Set[str] = field(default_factory=set)
    gates: Set[str] = field(default_factory=set)
    viewpoint: Dict[str, Any] = field(default_factory=dict)
    beats: Set[str] = field(default_factory=set)

    def add_beat(self, beat: Optional[str]) -> None:
        if isinstance(beat, str) and beat:
            self.beats.add(beat)


def _coerce_str_set(values: Any) -> Set[str]:
    if isinstance(values, str):
        return {values}
    if isinstance(values, Mapping):
        return {str(item) for item in values.values() if isinstance(item, str)}
    if isinstance(values, Iterable) and not isinstance(values, (str, bytes)):
        return {str(item) for item in values if isinstance(item, (str, bytes))}
    return set()


def _merge_collections(target: Set[str], value: Any) -> None:
    target.update(_coerce_str_set(value))


def normalize_active(active: Mapping[str, Any] | ActiveState | None) -> ActiveState:
    """Normalize arbitrary active inputs into an ActiveState."""

    if isinstance(active, ActiveState):
        return active

    state = ActiveState()
    if not isinstance(active, Mapping):
        return state

    _merge_collections(state.schemas, active.get("schemas"))
    _merge_collections(state.metaphors, active.get("metaphors"))
    _merge_collections(state.gates, active.get("gates"))
    _merge_collections(state.beats, active.get("beats"))
    state.add_beat(active.get("beat"))

    viewpoint = active.get("viewpoint")
    if isinstance(viewpoint, Mapping):
        state.viewpoint = dict(viewpoint)

    return state


def extract_active_from_trace(trace: Mapping[str, Any]) -> ActiveState:
    """Derive the active state from a composer trace-like structure."""

    if not isinstance(trace, Mapping):
        return ActiveState()

    buckets: Dict[str, Set[str]] = {
        "schemas": set(),
        "metaphors": set(),
        "gates": set(),
        "beats": set(),
    }

    def collect(mapping: Mapping[str, Any]) -> None:
        for key in ("schemas", "selected_schemas"):
            _merge_collections(buckets["schemas"], mapping.get(key))
        for key in ("metaphors", "selected_metaphors"):
            _merge_collections(buckets["metaphors"], mapping.get(key))
        for key in ("gates", "selected_gates"):
            _merge_collections(buckets["gates"], mapping.get(key))
        for key in ("beats", "selected_beats"):
            _merge_collections(buckets["beats"], mapping.get(key))
        beat = mapping.get("beat")
        if isinstance(beat, str):
            buckets["beats"].add(beat)

    collect(trace)
    for nested_key in ("selected", "active", "frame"):
        nested = trace.get(nested_key)
        if isinstance(nested, Mapping):
            collect(nested)

    viewpoint: Dict[str, Any] = {}
    for key in ("viewpoint", "vp", "view"):
        candidate = trace.get(key)
        if isinstance(candidate, Mapping):
            viewpoint = dict(candidate)
            break
    else:
        steps = trace.get("steps")
        if isinstance(steps, Sequence):
            for step in reversed(steps):
                if not isinstance(step, Mapping):
                    continue
                for key in ("viewpoint", "vp"):
                    candidate = step.get(key)
                    if isinstance(candidate, Mapping):
                        viewpoint = dict(candidate)
                        break
                if viewpoint:
                    break

    normalized = ActiveState()
    normalized.schemas = buckets["schemas"]
    normalized.metaphors = buckets["metaphors"]
    normalized.gates = buckets["gates"]
    normalized.beats = buckets["beats"]
    if viewpoint:
        normalized.viewpoint = viewpoint
    return normalized


def _has_explicit_cue(viewpoint: Mapping[str, Any], key: str) -> bool:
    if not viewpoint:
        return False
    if bool(viewpoint.get("explicit")):
        return True
    cues = viewpoint.get("cues")
    if isinstance(cues, Mapping):
        return bool(cues.get(key))
    if isinstance(cues, Sequence) and not isinstance(cues, (str, bytes)):
        return key in {str(item) for item in cues}
    return False


def _alias_beat(beat: str) -> str:
    return _BEAT_ALIASES.get(beat, beat)


def _beat_weight(frame: FrameItem, beat: str) -> Optional[float]:
    canonical = _alias_beat(beat)
    weight = frame.beat_affinity.get(beat)
    if weight is None:
        weight = frame.beat_affinity.get(canonical)
    if weight is None or canonical not in _ALLOWED_BEATS:
        return None
    try:
        return float(weight)
    except (TypeError, ValueError):
        return None


def check_frame(active: Mapping[str, Any] | ActiveState | None, frame: FrameItem) -> Dict[str, Any]:
    """Check whether the active selection coheres with the frame."""

    state = normalize_active(active)

    issues: List[Tuple[str, Dict[str, Any]]] = []
    blocking_codes: Set[str] = set()

    allowed_schema_set = set(frame.allowed_schemas)
    required_schema_set = set(frame.required_schemas)
    disallowed_schema_set = set(frame.disallowed_schemas)
    allowed_metaphor_set = set(frame.allowed_metaphors)
    disallowed_metaphor_set = set(frame.disallowed_metaphors)

    missing_required = sorted(required_schema_set - state.schemas)
    if missing_required:
        detail = {"code": FRM_MISSING_REQUIRED_SCHEMA, "missing": missing_required}
        issues.append((FRM_MISSING_REQUIRED_SCHEMA, detail))
        blocking_codes.add(FRM_MISSING_REQUIRED_SCHEMA)

    disallowed_explicit = state.schemas & disallowed_schema_set
    if disallowed_explicit:
        detail = {
            "code": FRM_DISALLOWED_SCHEMA,
            "schemas": sorted(disallowed_explicit),
            "category": "disallowed",
        }
        issues.append((FRM_DISALLOWED_SCHEMA, detail))
        blocking_codes.add(FRM_DISALLOWED_SCHEMA)

    if allowed_schema_set:
        not_allowed = {schema for schema in state.schemas if schema not in allowed_schema_set}
        if not_allowed:
            detail = {
                "code": FRM_DISALLOWED_SCHEMA,
                "schemas": sorted(not_allowed),
                "category": "not_allowed",
            }
            issues.append((FRM_DISALLOWED_SCHEMA, detail))
            blocking_codes.add(FRM_DISALLOWED_SCHEMA)

    disallowed_met = state.metaphors & disallowed_metaphor_set
    if disallowed_met:
        detail = {
            "code": FRM_DISALLOWED_METAPHOR,
            "metaphors": sorted(disallowed_met),
            "category": "disallowed",
        }
        issues.append((FRM_DISALLOWED_METAPHOR, detail))
        blocking_codes.add(FRM_DISALLOWED_METAPHOR)

    if allowed_metaphor_set:
        not_allowed_met = {
            metaphor for metaphor in state.metaphors if metaphor not in allowed_metaphor_set
        }
        if not_allowed_met:
            detail = {
                "code": FRM_DISALLOWED_METAPHOR,
                "metaphors": sorted(not_allowed_met),
                "category": "not_allowed",
            }
            issues.append((FRM_DISALLOWED_METAPHOR, detail))
            blocking_codes.add(FRM_DISALLOWED_METAPHOR)

    gates_allowed_set = set(frame.gates_allowed)

    if gates_allowed_set:
        not_allowed_gates = {
            gate for gate in state.gates if gate not in gates_allowed_set
        }
        if not_allowed_gates:
            detail = {
                "code": FRM_GATE_NOT_ALLOWED,
                "gates": sorted(not_allowed_gates),
            }
            issues.append((FRM_GATE_NOT_ALLOWED, detail))
            blocking_codes.add(FRM_GATE_NOT_ALLOWED)

    mismatched_view = []
    for key in ("person", "tense", "distance"):
        default_value = getattr(frame.viewpoint_defaults, key, None)
        actual_value = state.viewpoint.get(key)
        if default_value and actual_value and default_value != actual_value:
            if not _has_explicit_cue(state.viewpoint, key):
                mismatched_view.append((key, default_value, actual_value))
    if mismatched_view:
        detail = {
            "code": FRM_VIEWPOINT_MISMATCH,
            "mismatch": [
                {"feature": feature, "expected": expected, "actual": actual}
                for feature, expected, actual in mismatched_view
            ],
        }
        issues.append((FRM_VIEWPOINT_MISMATCH, detail))
        blocking_codes.add(FRM_VIEWPOINT_MISMATCH)

    weak_beats: List[Dict[str, Any]] = []
    for beat in state.beats:
        weight = _beat_weight(frame, beat)
        if weight is None:
            weak_beats.append({"beat": beat, "weight": None})
        elif weight < 0.5:
            weak_beats.append({"beat": beat, "weight": weight})
    if weak_beats:
        detail = {"code": FRM_BEAT_AFFINITY_WEAK, "beats": weak_beats}
        issues.append((FRM_BEAT_AFFINITY_WEAK, detail))

    reasons = [code for code, _ in issues]
    details = [detail for _, detail in issues]
    blocking = any(code in blocking_codes for code in reasons)

    return {"pass": not blocking, "reasons": reasons, "details": details}
