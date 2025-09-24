"""Expectation curve utilities and explosion detection."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableSequence, Optional, Sequence

from sv_sdk.loader import METAPHORS_PATH, file_sha256, load_metaphor_bank, load_yaml
from sv_sdk.models import MetaphorBank, MetaphorItem

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
BEATS_CONFIG_PATH = CONFIG_DIR / "beats.yml"
THRESHOLDS_CONFIG_PATH = CONFIG_DIR / "thresholds.yml"


def _safe_load_yaml(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    data = load_yaml(path)
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def _beats_config() -> Dict[str, object]:
    return _safe_load_yaml(BEATS_CONFIG_PATH)


@lru_cache(maxsize=1)
def _thresholds_config() -> Dict[str, object]:
    return _safe_load_yaml(THRESHOLDS_CONFIG_PATH)


def _expectation_targets(base: str) -> Mapping[str, float]:
    config = _beats_config()
    targets = config.get("expectation_targets", {})
    if not isinstance(targets, Mapping) or not targets:
        beats_config = config.get("beats", [])
        if isinstance(beats_config, Sequence):
            linear: Dict[str, float] = {}
            for beat in beats_config:
                if isinstance(beat, Mapping):
                    name = beat.get("name")
                    target = beat.get("expectation_target")
                    if isinstance(name, str) and isinstance(target, (int, float)):
                        linear[name] = float(target)
            if linear:
                targets = {"linear": linear}
    if not isinstance(targets, Mapping):
        raise ValueError("config/beats.yml missing expectation_targets mapping")

    curve = targets.get(base)
    if not isinstance(curve, Mapping):
        available = ", ".join(sorted(targets.keys())) if targets else "<none>"
        raise ValueError(f"Unknown expectation base '{base}'. Available: {available}")
    return curve  # type: ignore[return-value]


def _default_beats() -> Sequence[str]:
    config = _beats_config()
    beats = config.get("beat_order")
    if isinstance(beats, Sequence) and not isinstance(beats, (str, bytes)):
        return [str(beat) for beat in beats]
    # Sensible default ordering when config is absent.
    return ["hook", "setup", "development", "turn", "reveal", "settle"]


def build_curve(beats: Sequence[str], base: str = "linear") -> List[float]:
    """Produce a monotonic expectation curve for the supplied beats."""

    beats = list(beats)
    if not beats:
        return []

    targets = _expectation_targets(base)
    # Fallback increment when a beat lacks explicit configuration.
    fallback_step = 1.0 / max(len(beats) - 1, 1)

    curve: List[float] = []
    last_value = 0.0
    for index, beat in enumerate(beats):
        configured = targets.get(beat)
        if isinstance(configured, (int, float)):
            value = float(configured)
        else:
            value = last_value + fallback_step
        value = max(last_value, min(1.0, value))
        if index == len(beats) - 1:
            value = 1.0
        curve.append(value)
        last_value = value
    return curve


def _metaphor_index(bank: MetaphorBank) -> Dict[str, MetaphorItem]:
    return {metaphor.id: metaphor for metaphor in bank.metaphors}


def _ensure_monotonic(curve: MutableSequence[float]) -> None:
    for index in range(1, len(curve)):
        if curve[index] < curve[index - 1]:
            curve[index] = curve[index - 1]
    if curve:
        curve[-1] = max(curve[-1], 1.0)
        # Clamp to 1.0 to avoid numeric drift above 1
        for index, value in enumerate(curve):
            if value > 1.0:
                curve[index] = 1.0


def apply_metaphor_bias(
    curve: Sequence[float],
    active_metaphors: Iterable[str],
    bank: MetaphorBank,
    *,
    beats: Optional[Sequence[str]] = None,
) -> List[float]:
    """Apply gating increments for active metaphors and return the biased curve."""

    biased = list(curve)
    if not biased:
        return biased

    beats = list(beats) if beats is not None else list(_default_beats())
    beat_to_index = {beat: index for index, beat in enumerate(beats)}
    metaphors = _metaphor_index(bank)

    for metaphor_id in active_metaphors:
        metaphor = metaphors.get(metaphor_id)
        if metaphor is None:
            continue
        bias = metaphor.gating.beats_bias
        if isinstance(bias, str):
            targets = [bias]
        elif isinstance(bias, Iterable):
            targets = [str(item) for item in bias]
        else:
            targets = []

        increment = float(metaphor.gating.expectation_increment)
        for beat in targets:
            index = beat_to_index.get(beat)
            if index is None:
                continue
            biased[index] = min(1.0, biased[index] + increment)

    _ensure_monotonic(biased)
    return biased


def find_explosion_step(curve: Sequence[float], thresholds: Mapping[str, object]) -> Dict[str, object]:
    """Locate the first beat that meets the explosion threshold."""

    if not curve:
        return {"beat_index": -1, "value": 0.0, "reason": "no_beats"}

    threshold = float(thresholds.get("threshold", 0.8))
    min_index = int(thresholds.get("min_index", 0))
    max_index = int(thresholds.get("max_index", len(curve) - 1))

    for index, value in enumerate(curve):
        if value >= threshold:
            if index < min_index:
                reason = "before_window"
            elif index > max_index:
                reason = "after_window"
            else:
                reason = "within_window"
            return {"beat_index": index, "value": value, "reason": reason}

    # Threshold never reached; report the highest value and mark as deferred.
    return {
        "beat_index": len(curve) - 1,
        "value": curve[-1],
        "reason": "threshold_not_reached",
    }


def _explosion_thresholds() -> Mapping[str, object]:
    config = _thresholds_config()
    window = config.get("explosion_timing_range", [])
    target = config.get("explosion_timing_target", 0.85)
    if isinstance(window, Mapping):
        merged = dict(window)
        merged.setdefault("threshold", target)
        return merged
    if isinstance(window, Sequence) and len(window) == 2:
        low, high = window
        return {
            "threshold": float(target),
            "range": [float(low), float(high)],
        }
    return {"threshold": float(target)}


def compute_expectation_trace(
    beats: Sequence[str],
    active_metaphors: Iterable[str],
    *,
    bank: Optional[MetaphorBank] = None,
    base: str = "linear",
) -> Dict[str, object]:
    """Compute expectation curves and explosion diagnostics for the supplied beats."""

    beats = list(beats)
    active_list = list(active_metaphors)
    metaphor_bank = bank or load_metaphor_bank()

    curve_before = build_curve(beats, base=base)
    curve_after = apply_metaphor_bias(curve_before, active_list, metaphor_bank, beats=beats)

    thresholds = _explosion_thresholds()
    fire = find_explosion_step(curve_after, thresholds)

    trace = {
        "beats": beats,
        "curve_before": curve_before,
        "curve_after": curve_after,
        "active_metaphors": active_list,
        "fired_step": fire,
    }
    return trace


@lru_cache(maxsize=1)
def metaphor_bank_sha() -> str:
    """Return the SHA-256 digest of the metaphor bible."""

    return file_sha256(METAPHORS_PATH)


def expectation_curve(step: int, base: str = "linear") -> float:
    """Backwards-compatible helper returning the expectation value at a step index."""

    beats = list(_default_beats())
    curve = build_curve(beats, base=base)
    if step < 1:
        return 0.0
    index = min(step - 1, len(curve) - 1)
    return curve[index]


def should_explode(step: int, threshold: Optional[float] = None) -> bool:
    """Backwards-compatible helper to test whether an explosion should trigger."""

    thresholds = _explosion_thresholds()
    target = threshold if threshold is not None else float(thresholds.get("threshold", 0.8))
    value = expectation_curve(step)
    return value >= target


def default_beats() -> List[str]:
    """Expose the configured beat order for external callers."""

    return list(_default_beats())
