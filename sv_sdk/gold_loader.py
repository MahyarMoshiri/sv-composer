"""Loader utilities for the gold-labelled corpus."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from pydantic import ValidationError

from .models import GoldLabel, GoldSet, Span

DEFAULT_GOLD_PATH = Path(__file__).resolve().parents[1] / "data" / "gold" / "labels.jsonl"


def _normalize_strings(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, Mapping):
        return {key: _normalize_strings(value) for key, value in obj.items()}
    if isinstance(obj, Sequence) and not isinstance(obj, (bytes, bytearray, str)):
        return [_normalize_strings(item) for item in obj]
    return obj


def _ensure_provenance(payload: MutableMapping[str, Any]) -> None:
    if "provenance" in payload:
        return
    provenance_keys = ("curator", "source", "license", "confidence", "notes")
    provenance: dict[str, Any] = {}
    for key in provenance_keys:
        if key in payload:
            provenance[key] = payload.pop(key)
    if provenance:
        payload["provenance"] = provenance


def _coerce_span(span: Sequence[Any], *, context: str) -> Span:
    if not isinstance(span, Sequence) or isinstance(span, (str, bytes)):
        raise ValueError(f"{context} span must be a two-element sequence")
    if len(span) != 2:
        raise ValueError(f"{context} span must contain exactly two integers")
    try:
        start = int(span[0])
        end = int(span[1])
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"{context} span values must be integers") from exc
    if end <= start:
        raise ValueError(f"{context} span end must be greater than start")
    if start < 0 or end < 0:
        raise ValueError(f"{context} span positions must be non-negative")
    return (start, end)


def _dedupe_spans(spans: Iterable[Sequence[Any]], *, context: str) -> list[Span]:
    deduped: list[Span] = []
    seen: set[Span] = set()
    for span in spans:
        normalized = _coerce_span(span, context=context)
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _normalize_annotation_spans(entry_list: list[Any], *, context: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(entry_list):
        if not isinstance(raw, Mapping):
            raise ValueError(f"{context}[{index}] must be a mapping")
        item = dict(raw)
        identifier = item.get("id")
        if not isinstance(identifier, str):
            raise ValueError(f"{context}[{index}] requires an 'id' string")
        item["id"] = identifier
        spans = item.get("spans", [])
        if spans:
            item["spans"] = _dedupe_spans(spans, context=f"{context}[{index}]")
        else:
            item["spans"] = []
        normalized.append(item)
    return normalized


def _normalize_attention(entries: list[Any], *, context: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen_spans: set[Span] = set()
    for index, raw in enumerate(entries):
        if not isinstance(raw, Mapping):
            raise ValueError(f"{context}[{index}] must be a mapping")
        item = dict(raw)
        span = item.get("span")
        normalized_span = _coerce_span(span, context=f"{context}[{index}].span")
        if normalized_span in seen_spans:
            continue
        seen_spans.add(normalized_span)
        item["span"] = normalized_span
        normalized.append(item)
    return normalized


def _prepare_payload(payload: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    _ensure_provenance(payload)

    labels = payload.get("labels")
    if not isinstance(labels, MutableMapping):
        raise ValueError("labels block must be a mapping")

    schemas = labels.get("schemas")
    if isinstance(schemas, list):
        labels["schemas"] = _normalize_annotation_spans(schemas, context="labels.schemas")

    metaphors = labels.get("metaphors")
    if isinstance(metaphors, list):
        labels["metaphors"] = _normalize_annotation_spans(
            metaphors, context="labels.metaphors"
        )

    attention = labels.get("attention")
    if isinstance(attention, list):
        labels["attention"] = _normalize_attention(attention, context="labels.attention")

    explosion = labels.get("explosion")
    if isinstance(explosion, MutableMapping):
        beat = explosion.get("beat")
        if isinstance(beat, Sequence) and not isinstance(beat, (str, bytes)):
            raise ValueError("labels.explosion.beat must be an integer")

    frame = labels.get("frame")
    if frame is not None and not isinstance(frame, Mapping):
        raise ValueError("labels.frame must be a mapping or null")

    viewpoint = labels.get("viewpoint")
    if viewpoint is not None and not isinstance(viewpoint, Mapping):
        raise ValueError("labels.viewpoint must be a mapping or null")

    return payload


def load_gold_jsonl(path: str | Path = DEFAULT_GOLD_PATH) -> GoldSet:
    """Load and normalize the gold-labelled corpus."""

    gold_path = Path(path)
    records: GoldSet = []

    try:
        raw_lines = gold_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Gold corpus not found at {gold_path}") from exc

    for line_number, line in enumerate(raw_lines, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{gold_path}:{line_number}: invalid JSON: {exc.msg}") from exc

        normalized = _normalize_strings(parsed)
        if not isinstance(normalized, MutableMapping):
            raise ValueError(f"{gold_path}:{line_number}: root entry must be a mapping")

        try:
            prepared = _prepare_payload(normalized)
            label = GoldLabel.model_validate(prepared)
        except (ValueError, ValidationError) as exc:
            raise ValueError(f"{gold_path}:{line_number}: {exc}") from exc

        records.append(label)

    return records
