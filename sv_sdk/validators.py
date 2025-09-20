"""Validators for Schema Bank integrity."""
from __future__ import annotations

from typing import List

from .models import Lexeme, ParamSpec, SchemaBank


def _validate_param(schema_id: str, name: str, spec: ParamSpec, errors: List[str]) -> None:
    kind = spec.kind
    if kind == "enum":
        if not spec.values:
            errors.append(f"{schema_id}.params[{name}] enum must define values")
        if spec.default is not None and spec.values and spec.default not in spec.values:
            errors.append(
                f"{schema_id}.params[{name}] default {spec.default!r} not in enum values"
            )
        if spec.min is not None or spec.max is not None:
            errors.append(f"{schema_id}.params[{name}] enum should not define min/max")
    else:
        if spec.values:
            errors.append(f"{schema_id}.params[{name}] {kind} should not define values")
        for bound_name, bound_value in ("min", spec.min), ("max", spec.max):
            if bound_value is not None and not isinstance(bound_value, (int, float)):
                errors.append(
                    f"{schema_id}.params[{name}] {bound_name} must be numeric when provided"
                )
        if spec.min is not None and spec.max is not None and spec.min > spec.max:
            errors.append(f"{schema_id}.params[{name}] min cannot exceed max")
        if spec.default is not None and isinstance(spec.default, (int, float)):
            if spec.min is not None and spec.default < spec.min:
                errors.append(f"{schema_id}.params[{name}] default below minimum")
            if spec.max is not None and spec.default > spec.max:
                errors.append(f"{schema_id}.params[{name}] default above maximum")
    if kind == "bool" and spec.default is not None and not isinstance(spec.default, bool):
        errors.append(f"{schema_id}.params[{name}] bool default must be boolean")
    if kind == "int" and spec.default is not None and not isinstance(spec.default, int):
        errors.append(f"{schema_id}.params[{name}] int default must be integer")


def _validate_lexeme(schema_id: str, lang: str, lexeme: Lexeme, errors: List[str]) -> None:
    if not lexeme.lemma.strip():
        errors.append(f"{schema_id}.lexicon[{lang}] lemma must be non-empty")
    if not 0.0 <= lexeme.w <= 1.0:
        errors.append(f"{schema_id}.lexicon[{lang}] weight {lexeme.w} out of [0,1]")


def validate_schema_bank(bank: SchemaBank) -> None:
    """Validate schema bank invariants, raising ValueError on failure."""

    errors: List[str] = []
    seen_ids: set[str] = set()
    all_ids = {schema.id for schema in bank.schemas}

    for schema in bank.schemas:
        if schema.id in seen_ids:
            errors.append(f"duplicate schema id: {schema.id}")
        seen_ids.add(schema.id)

        for name, spec in schema.params.items():
            _validate_param(schema.id, name, spec, errors)

        if not -1.0 <= schema.affect.valence <= 1.0:
            errors.append(f"{schema.id}.affect.valence outside [-1,1]: {schema.affect.valence}")
        if not 0.0 <= schema.affect.arousal <= 1.0:
            errors.append(f"{schema.id}.affect.arousal outside [0,1]: {schema.affect.arousal}")

        lexicon_dict = schema.lexicon.model_dump()
        for lang, lexemes in lexicon_dict.items():
            if not isinstance(lexemes, list):
                continue
            for lexeme_data in lexemes:
                lexeme = Lexeme.model_validate(lexeme_data)
                _validate_lexeme(schema.id, lang, lexeme, errors)

        for target in schema.coactivate:
            if target not in all_ids:
                errors.append(f"{schema.id}.coactivate references unknown id {target}")

    if errors:
        joined = "\n".join(errors)
        raise ValueError(f"Schema bank validation failed:\n{joined}")
