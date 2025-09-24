"""Utilities for normalizing the schema bible into a spec-compliant form."""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml

from sv_control.lexicon import infer_weights_if_missing

DEFAULT_VERSION = "0.1.0"
DEFAULT_VALENCE = 0.0
DEFAULT_AROUSAL = 0.5
DEFAULT_PROVENANCE = {
    "source": "SV_Extended",
    "curator": "unknown",
    "license": "CC-BY",
    "confidence": 0.5,
}


@dataclass
class Report:
    missing_fields: List[str]
    inferred_params: List[str]
    todos: List[str]

    def add_missing(self, message: str) -> None:
        self.missing_fields.append(message)

    def add_param(self, message: str) -> None:
        self.inferred_params.append(message)

    def add_todo(self, message: str) -> None:
        self.todos.append(message)


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Schema source file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {path}, found {type(data)!r}")
    return data


def _ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Cannot coerce value {value!r} to float")


def _normalize_param(schema_id: str, name: str, value: Any, report: Report) -> Tuple[str, Dict[str, Any]]:
    spec: Dict[str, Any]
    rule = "unknown"

    if isinstance(value, dict) and "type" in value:
        spec = dict(value)
        rule = "existing spec"
    elif isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            spec = {"type": "enum", "values": list(value)}
            rule = "enum-from-list"
        elif len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
            low, high = value
            spec = {"type": "float", "min": float(low), "max": float(high)}
            rule = "range-from-two-values"
        else:
            spec = {"type": "enum", "values": [str(item) for item in value]}
            rule = "enum-from-generic-list"
            report.add_todo(
                f"{schema_id}.params.{name}: review inferred enum values {spec['values']}"
            )
    elif isinstance(value, tuple) and len(value) == 2 and all(
        isinstance(item, (int, float)) for item in value
    ):
        low, high = value
        spec = {"type": "float", "min": float(low), "max": float(high)}
        rule = "range-from-tuple"
    elif isinstance(value, bool):
        spec = {"type": "bool", "default": bool(value)}
        rule = "bool-default"
    elif isinstance(value, int):
        spec = {"type": "int", "default": int(value)}
        rule = "int-default"
    elif isinstance(value, float):
        spec = {"type": "float", "default": float(value)}
        rule = "float-default"
    elif isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            spec = {"type": "enum", "values": [cleaned], "default": cleaned}
            rule = "enum-from-string"
            report.add_todo(
                f"{schema_id}.params.{name}: confirm singleton enum derived from string value"
            )
        else:
            spec = {"type": "enum", "values": []}
            rule = "empty-string"
            report.add_todo(f"{schema_id}.params.{name}: no data available; please populate")
    elif value is None:
        spec = {"type": "enum", "values": []}
        rule = "missing"
        report.add_todo(f"{schema_id}.params.{name}: missing value; please populate")
    else:
        spec = {"type": "enum", "values": [str(value)]}
        rule = "enum-from-unknown"
        report.add_todo(
            f"{schema_id}.params.{name}: coerced to enum using string representation {spec['values']}"
        )

    report.add_param(f"{schema_id}.params.{name}: inferred via {rule}")
    return name, spec


def _normalize_affect(schema_id: str, raw_affect: Any, report: Report) -> Dict[str, Any]:
    affect: Dict[str, Any] = {}
    if isinstance(raw_affect, dict):
        affect.update(raw_affect)
    else:
        if raw_affect not in (None, {}):
            report.add_todo(f"{schema_id}.affect: unexpected format; replaced with defaults")

    valence = affect.get("valence", DEFAULT_VALENCE)
    arousal = affect.get("arousal", DEFAULT_AROUSAL)
    try:
        valence_f = max(-1.0, min(1.0, float(valence)))
    except (TypeError, ValueError):
        valence_f = DEFAULT_VALENCE
        report.add_todo(f"{schema_id}.affect.valence: could not parse; defaulted to {valence_f}")
    try:
        arousal_f = max(0.0, min(1.0, float(arousal)))
    except (TypeError, ValueError):
        arousal_f = DEFAULT_AROUSAL
        report.add_todo(f"{schema_id}.affect.arousal: could not parse; defaulted to {arousal_f}")

    affect["valence"] = valence_f
    affect["arousal"] = arousal_f
    if "tags" in affect and not isinstance(affect["tags"], list):
        affect["tags"] = _ensure_list(affect["tags"])
    return affect


def _normalize_lexicon(schema_id: str, raw_lexicon: Any, report: Report) -> Dict[str, Any]:
    languages = {"en": [], "fa": []}
    if isinstance(raw_lexicon, dict):
        items = raw_lexicon
    else:
        items = {}
        if raw_lexicon:
            report.add_todo(f"{schema_id}.lexicon: unexpected format; replaced with defaults")

    for lang in set(languages) | set(items):
        lang_entries: List[Dict[str, Any]] = []
        raw_entries = items.get(lang, [])
        if isinstance(raw_entries, dict):
            raw_entries = list(raw_entries.values())
        for entry in _ensure_list(raw_entries):
            normalized: Dict[str, Any]
            if isinstance(entry, dict):
                normalized = {
                    "lemma": str(entry.get("lemma", "")).strip(),
                    "w": entry.get("w"),
                }
            else:
                normalized = {"lemma": str(entry).strip(), "w": None}
            normalized = infer_weights_if_missing(normalized)
            if not normalized["lemma"]:
                report.add_todo(f"{schema_id}.lexicon[{lang}]: empty lemma removed")
                continue
            lang_entries.append(normalized)
        languages[lang] = lang_entries
    return languages


def _normalize_examples(raw_examples: Any) -> Dict[str, List[str]]:
    if isinstance(raw_examples, dict):
        text = _ensure_list(raw_examples.get("text", []))
        visual = _ensure_list(raw_examples.get("visual", []))
    else:
        text = []
        visual = []
    text = [str(item) for item in text if str(item).strip()]
    visual = [str(item) for item in visual if str(item).strip()]
    return {"text": text, "visual": visual}


def _normalize_provenance(schema_id: str, raw_prov: Any, report: Report) -> Dict[str, Any]:
    provenance = dict(DEFAULT_PROVENANCE)
    if isinstance(raw_prov, dict):
        provenance.update({k: v for k, v in raw_prov.items() if v is not None})
    else:
        if raw_prov not in (None, {}):
            report.add_todo(f"{schema_id}.provenance: unexpected format; replaced with defaults")
    return provenance


def _ensure_title(schema_id: str, raw: Dict[str, Any], report: Report) -> str:
    title = str(raw.get("title") or "").strip()
    if not title:
        guessed = schema_id.replace("_", " ").title() if schema_id else "Untitled Schema"
        report.add_missing(f"{schema_id}: title missing; set to '{guessed}'")
        return guessed
    return title


def _ensure_definition(schema_id: str, raw: Dict[str, Any], report: Report) -> str:
    definition = str(raw.get("definition") or "").strip()
    if not definition:
        placeholder = f"TODO: provide definition for {schema_id}"
        report.add_missing(f"{schema_id}: definition missing; added placeholder")
        report.add_todo(f"{schema_id}: replace placeholder definition")
        return placeholder
    return definition


def _normalize_schema(schema: Dict[str, Any], report: Report) -> Dict[str, Any]:
    schema_id = str(schema.get("id") or "").strip()
    if not schema_id:
        raise ValueError("Encountered schema without an 'id'")

    normalized: Dict[str, Any] = {"id": schema_id}
    normalized["title"] = _ensure_title(schema_id, schema, report)
    normalized["definition"] = _ensure_definition(schema_id, schema, report)

    roles = schema.get("roles", [])
    normalized["roles"] = [str(role).strip() for role in _ensure_list(roles) if str(role).strip()]

    raw_params = schema.get("params", {})
    params: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw_params, dict):
        iterator: Iterable[Tuple[str, Any]] = raw_params.items()
    else:
        iterator = []
        report.add_todo(f"{schema_id}.params: unexpected format; replaced with empty mapping")
    for name, value in iterator:
        key, spec = _normalize_param(schema_id, str(name), value, report)
        params[key] = spec
    normalized["params"] = params

    normalized["affect"] = _normalize_affect(schema_id, schema.get("affect"), report)
    normalized["lexicon"] = _normalize_lexicon(schema_id, schema.get("lexicon"), report)

    coactivate = schema.get("coactivate", [])
    if not isinstance(coactivate, list):
        report.add_todo(f"{schema_id}.coactivate: unexpected format converted to list")
        coactivate = _ensure_list(coactivate)
    normalized["coactivate"] = [str(item).strip() for item in coactivate if str(item).strip()]

    normalized["examples"] = _normalize_examples(schema.get("examples"))
    normalized["provenance"] = _normalize_provenance(schema_id, schema.get("provenance"), report)

    return normalized


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def _write_report(path: Path, report: Report) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Schema Normalization Report", ""]

    if report.missing_fields:
        lines.extend(["## Missing Fields Filled", ""])
        lines.extend(f"- {item}" for item in report.missing_fields)
        lines.append("")

    if report.inferred_params:
        lines.extend(["## Parameter Inference", ""])
        lines.extend(f"- {item}" for item in report.inferred_params)
        lines.append("")

    if report.todos:
        lines.extend(["## TODO", ""])
        lines.extend(f"- {item}" for item in report.todos)
        lines.append("")

    if len(lines) == 2:
        lines.append("No adjustments required. Source already conformed to schema spec.")

    with path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")


def normalize(raw_path: Path, out_path: Path, report_path: Path) -> None:
    raw_data = _load_yaml(raw_path)
    report = Report(missing_fields=[], inferred_params=[], todos=[])

    schemas = raw_data.get("schemas", [])
    if not isinstance(schemas, list):
        raise ValueError("Expected 'schemas' to be a list in the source YAML")

    normalized_bank: Dict[str, Any] = {
        "version": str(raw_data.get("version") or DEFAULT_VERSION),
        "schemas": [],
    }
    if "version" not in raw_data:
        report.add_missing(f"Top-level version missing; defaulted to {DEFAULT_VERSION}")

    for schema in schemas:
        if not isinstance(schema, dict):
            raise ValueError("Each schema entry must be a mapping")
        normalized_schema = _normalize_schema(schema, report)
        normalized_bank["schemas"].append(normalized_schema)

    _write_yaml(out_path, normalized_bank)
    _write_report(report_path, report)


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize bible schemas into spec-compliant form")
    parser.add_argument("--in", dest="in_path", required=True, help="Path to raw schemas YAML")
    parser.add_argument(
        "--out", dest="out_path", required=True, help="Destination path for normalized YAML"
    )
    parser.add_argument(
        "--report",
        dest="report_path",
        required=True,
        help="Path to write the human-readable normalization report",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = _parse_args(list(argv or sys.argv[1:]))
    raw_path = Path(args.in_path)
    out_path = Path(args.out_path)
    report_path = Path(args.report_path)

    try:
        normalize(raw_path=raw_path, out_path=out_path, report_path=report_path)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Normalization failed: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
