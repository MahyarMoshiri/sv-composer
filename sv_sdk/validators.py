"""Validators for Schema Bank integrity."""
from __future__ import annotations

import warnings
from typing import Dict, List, Mapping, Optional, Sequence, Set

from .loader import BIBLE_DIR, load_metaphor_bank, load_schema_bank, load_yaml
from .models import (
    BeatsConfig,
    BlendRules,
    FrameBank,
    Lexeme,
    MetaphorBank,
    MetaphorItem,
    ParamSpec,
    Span,
    GoldSet,
    SchemaBank,
)


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


def _frame_ids() -> Optional[Set[str]]:
    """Return the set of frame identifiers when frames.yml is available."""

    frames_path = BIBLE_DIR / "frames.yml"
    try:
        data = load_yaml(frames_path)
    except FileNotFoundError:
        warnings.warn(
            "bible/frames.yml not found; skipping preferred_frames validation",
            stacklevel=2,
        )
        return None

    frames = data.get("frames", [])
    ids: Set[str] = set()
    for entry in frames:
        if isinstance(entry, dict):
            identifier = entry.get("id")
            if isinstance(identifier, str):
                ids.add(identifier)
    return ids


def _gate_ids() -> Optional[Set[str]]:
    """Return the set of gate identifiers when gates.yml is available."""

    gates_path = BIBLE_DIR / "gates.yml"
    try:
        data = load_yaml(gates_path)
    except FileNotFoundError:
        warnings.warn(
            "bible/gates.yml not found; skipping gates_allowed validation",
            stacklevel=2,
        )
        return None

    gates = data.get("gates", [])
    ids: Set[str] = set()
    for entry in gates:
        if isinstance(entry, str):
            ids.add(entry)
        elif isinstance(entry, dict):
            identifier = entry.get("id")
            if isinstance(identifier, str):
                ids.add(identifier)
    return ids


def _validate_metaphor_lexicon(metaphor: MetaphorItem, errors: List[str]) -> None:
    for lang, lexemes in metaphor.lexicon.model_dump().items():
        if not isinstance(lexemes, list):
            continue
        for lexeme_data in lexemes:
            lexeme = Lexeme.model_validate(lexeme_data)
            if not 0.0 <= lexeme.w <= 1.0:
                errors.append(f"{metaphor.id}.lexicon[{lang}] weight {lexeme.w} out of [0,1]")


def _validate_metaphor_affect(metaphor: MetaphorItem, errors: List[str]) -> None:
    if not -1.0 <= metaphor.affect.valence <= 1.0:
        errors.append(
            f"{metaphor.id}.affect.valence outside [-1,1]: {metaphor.affect.valence}"
        )
    for pole, affect in metaphor.pole_affect.items():
        if not -1.0 <= affect.valence <= 1.0:
            errors.append(
                f"{metaphor.id}.pole_affect[{pole}].valence outside [-1,1]: {affect.valence}"
            )


def _validate_metaphor_cross_refs(
    metaphor: MetaphorItem,
    schema_ids: Set[str],
    frame_ids: Optional[Set[str]],
    errors: List[str],
    warnings_out: List[str],
) -> None:
    if metaphor.source_schema and metaphor.source_schema not in schema_ids:
        errors.append(
            f"{metaphor.id}.source_schema references unknown schema {metaphor.source_schema}"
        )

    for schema_id in metaphor.coactivate_schemas:
        if schema_id not in schema_ids:
            errors.append(
                f"{metaphor.id}.coactivate_schemas references unknown schema {schema_id}"
            )

    if frame_ids is not None:
        for frame_id in metaphor.preferred_frames:
            if frame_id not in frame_ids:
                warnings_out.append(
                    f"{metaphor.id}.preferred_frames references unknown frame {frame_id}"
                )


def validate_metaphor_bank(bank: MetaphorBank) -> List[str]:
    """Validate metaphor bank invariants, returning warnings on success."""

    errors: List[str] = []
    warnings_out: List[str] = []
    seen_ids: Set[str] = set()

    schema_bank = load_schema_bank()
    schema_ids = {schema.id for schema in schema_bank.schemas}
    frame_ids = _frame_ids()
    if frame_ids is None:
        warnings_out.append("frames.yml missing; preferred_frames not validated")

    all_metaphor_ids = {metaphor.id for metaphor in bank.metaphors}

    for metaphor in bank.metaphors:
        if metaphor.id in seen_ids:
            errors.append(f"duplicate metaphor id: {metaphor.id}")
        seen_ids.add(metaphor.id)

        if metaphor.type not in {"primary", "bipolar"}:
            errors.append(f"{metaphor.id}.type must be primary or bipolar")

        _validate_metaphor_lexicon(metaphor, errors)
        _validate_metaphor_affect(metaphor, errors)

        increment = metaphor.gating.expectation_increment
        if not 0.0 <= increment <= 1.0:
            errors.append(
                f"{metaphor.id}.gating.expectation_increment {increment} outside [0,1]"
            )

        _validate_metaphor_cross_refs(
            metaphor,
            schema_ids,
            frame_ids,
            errors,
            warnings_out,
        )

        for banned_id in metaphor.banned_with:
            if banned_id not in all_metaphor_ids:
                errors.append(
                    f"{metaphor.id}.banned_with references unknown metaphor {banned_id}"
                )

        if metaphor.type == "bipolar":
            if len(metaphor.bipolar) < 2:
                errors.append(f"{metaphor.id}.bipolar must define at least two poles")
            for pole in metaphor.bipolar:
                if pole not in metaphor.pole_affect:
                    errors.append(
                        f"{metaphor.id}.pole_affect missing entry for pole {pole}"
                    )

    if errors:
        joined = "\n".join(errors)
        raise ValueError(f"Metaphor bank validation failed:\n{joined}")

    return warnings_out


def _validate_attention_hint(frame_id: str, hint_index: int, hint: Dict[str, object], errors: List[str]) -> None:
    role = hint.get("role")
    schema = hint.get("schema")
    if not role and not schema:
        errors.append(f"{frame_id}.attention_defaults[{hint_index}] must define role or schema")
    weight = hint.get("w")
    try:
        numeric = float(weight)
    except (TypeError, ValueError):
        errors.append(
            f"{frame_id}.attention_defaults[{hint_index}].w must be numeric"
        )
        return
    if not 0.0 <= numeric <= 1.0:
        errors.append(
            f"{frame_id}.attention_defaults[{hint_index}].w {numeric} outside [0,1]"
        )


_ALLOWED_BEATS = {"hook", "setup", "development", "turn", "reveal", "settle"}
_BEAT_ALIASES = {"hook_out": "settle"}


def validate_frame_bank(bank: FrameBank) -> List[str]:
    """Validate frame bank invariants, returning warnings on success."""

    errors: List[str] = []
    warnings_out: List[str] = []
    seen_ids: Set[str] = set()

    schema_bank = load_schema_bank()
    schema_ids = {schema.id for schema in schema_bank.schemas}

    metaphor_bank = load_metaphor_bank()
    metaphor_ids = {metaphor.id for metaphor in metaphor_bank.metaphors}

    gate_ids = _gate_ids()
    if gate_ids is None:
        warnings_out.append("gates.yml missing; gates_allowed not validated")

    for frame in bank.frames:
        if frame.id in seen_ids:
            errors.append(f"duplicate frame id: {frame.id}")
        seen_ids.add(frame.id)

        combined_roles = set(frame.core_roles) | set(frame.optional_roles)
        for note_key in frame.role_notes:
            if note_key not in combined_roles:
                warnings_out.append(
                    f"{frame.id}.role_notes references unknown role '{note_key}'"
                )

        allowed_schemas = set(frame.allowed_schemas)
        required_schemas = set(frame.required_schemas)
        disallowed_schemas = set(frame.disallowed_schemas)

        missing_allowed = required_schemas - allowed_schemas
        if missing_allowed:
            errors.append(
                f"{frame.id}.required_schemas missing from allowed_schemas: {sorted(missing_allowed)}"
            )

        for schema_id in allowed_schemas | required_schemas | disallowed_schemas:
            if schema_id not in schema_ids:
                errors.append(
                    f"{frame.id}.schemas references unknown schema {schema_id}"
                )

        allowed_metaphors = set(frame.allowed_metaphors)
        disallowed_metaphors = set(frame.disallowed_metaphors)

        for metaphor_id in allowed_metaphors | disallowed_metaphors:
            if metaphor_id not in metaphor_ids:
                errors.append(
                    f"{frame.id}.metaphors references unknown metaphor {metaphor_id}"
                )

        for bias_id, weight in frame.metaphor_bias.items():
            if bias_id not in allowed_metaphors:
                errors.append(
                    f"{frame.id}.metaphor_bias references non-allowed metaphor {bias_id}"
                )
            if not 0.0 <= float(weight) <= 1.0:
                errors.append(
                    f"{frame.id}.metaphor_bias[{bias_id}] {weight} outside [0,1]"
                )

        for index, hint in enumerate(frame.attention_defaults):
            _validate_attention_hint(frame.id, index, hint.model_dump(by_alias=True), errors)

        if gate_ids is not None:
            for gate in frame.gates_allowed:
                if gate not in gate_ids:
                    errors.append(f"{frame.id}.gates_allowed references unknown gate {gate}")

        for beat_name, weight in frame.beat_affinity.items():
            canonical = _BEAT_ALIASES.get(beat_name, beat_name)
            if canonical not in _ALLOWED_BEATS:
                errors.append(
                    f"{frame.id}.beat_affinity includes unsupported beat '{beat_name}'"
                )
            if not 0.0 <= float(weight) <= 1.0:
                errors.append(
                    f"{frame.id}.beat_affinity[{beat_name}] {weight} outside [0,1]"
                )

        if len(frame.definition) > 160:
            warnings_out.append(
                f"{frame.id}.definition longer than 160 characters"
            )

    if errors:
        joined = "\n".join(errors)
        raise ValueError(f"Frame bank validation failed:\n{joined}")

    return warnings_out


def _allowed_langs() -> Set[str]:
    return {"en", "fa"}


def _allowed_explosion_beats(beats: BeatsConfig) -> Set[int]:
    explicit = {
        int(beat.order)
        for beat in beats.beats
        if beat.order is not None
    }
    if explicit:
        return {order for order in explicit if order > 0}
    if beats.beats:
        return {index + 1 for index, _ in enumerate(beats.beats)}
    # Sensible default when config is empty.
    return set()


def _has_viewpoint_cue(viewpoint: Mapping[str, object], feature: str) -> bool:
    if not viewpoint:
        return False
    if bool(viewpoint.get("explicit")):
        return True
    cues = viewpoint.get("cues")
    if isinstance(cues, Mapping):
        return bool(cues.get(feature))
    if isinstance(cues, Sequence) and not isinstance(cues, (str, bytes)):
        return feature in {str(item) for item in cues}
    return False


def _check_span_bounds(
    span: Span,
    text: str,
    *,
    label_id: str,
    context: str,
    errors: List[str],
) -> None:
    start, end = span
    length = len(text)
    if start >= length:
        errors.append(
            f"{label_id}: {context} span {span} starts beyond text length {length}"
        )
    if end > length:
        errors.append(
            f"{label_id}: {context} span {span} extends beyond text length {length}"
        )


def validate_gold(
    gold: GoldSet,
    schemas: SchemaBank,
    metaphors: MetaphorBank,
    frames: FrameBank,
    beats: BeatsConfig,
    *,
    errors_as: str = "raise",
) -> tuple[list[str], list[str]]:
    """Validate the gold-labelled corpus."""

    if errors_as not in {"raise", "list"}:
        raise ValueError("errors_as must be either 'raise' or 'list'")

    errors: list[str] = []
    warnings_out: list[str] = []

    seen_ids: Set[str] = set()
    allowed_langs = _allowed_langs()
    schema_ids = {schema.id for schema in schemas.schemas}
    metaphor_map = {metaphor.id: metaphor for metaphor in metaphors.metaphors}
    frame_map = {frame.id: frame for frame in frames.frames}
    bipolar_ids = {
        metaphor_id for metaphor_id, metaphor in metaphor_map.items() if metaphor.type == "bipolar"
    }
    allowed_beats = _allowed_explosion_beats(beats)

    for label in gold:
        if label.id in seen_ids:
            errors.append(f"duplicate gold id: {label.id}")
            continue
        seen_ids.add(label.id)

        if label.lang not in allowed_langs:
            errors.append(f"{label.id}: unsupported language '{label.lang}'")

        text = label.text
        for schema in label.labels.schemas:
            if schema.id not in schema_ids:
                errors.append(f"{label.id}: unknown schema '{schema.id}'")
            for span in schema.spans:
                _check_span_bounds(span, text, label_id=label.id, context=f"schema {schema.id}", errors=errors)

        for metaphor in label.labels.metaphors:
            metaphor_item = metaphor_map.get(metaphor.id)
            if metaphor_item is None:
                errors.append(f"{label.id}: unknown metaphor '{metaphor.id}'")
            elif metaphor.pole is not None and metaphor.id not in bipolar_ids:
                errors.append(
                    f"{label.id}: metaphor '{metaphor.id}' defines pole for non-bipolar metaphor"
                )
            for span in metaphor.spans:
                _check_span_bounds(
                    span,
                    text,
                    label_id=label.id,
                    context=f"metaphor {metaphor.id}",
                    errors=errors,
                )

        if label.labels.frame is not None:
            frame_id = label.labels.frame.id
            frame = frame_map.get(frame_id)
            if frame is None:
                errors.append(f"{label.id}: unknown frame '{frame_id}'")
            elif label.labels.viewpoint is not None:
                view = label.labels.viewpoint.model_dump()
                mismatches: list[tuple[str, str, str]] = []
                for feature in ("person", "tense", "distance"):
                    expected = getattr(frame.viewpoint_defaults, feature, None)
                    actual = view.get(feature)
                    if expected and actual and expected != actual:
                        if not _has_viewpoint_cue(view, feature):
                            mismatches.append((feature, expected, actual))
                if mismatches:
                    details = ", ".join(
                        f"{feature}: expected {exp}, saw {act}" for feature, exp, act in mismatches
                    )
                    warnings_out.append(f"{label.id}: viewpoint diverges from frame defaults ({details})")

        if label.labels.viewpoint is None and label.labels.frame is not None:
            frame_id = label.labels.frame.id
            if frame_id in frame_map:
                warnings_out.append(f"{label.id}: frame '{frame_id}' missing viewpoint annotation")

        for attention in label.labels.attention:
            weight = float(attention.w)
            if not 0.0 <= weight <= 1.0:
                errors.append(
                    f"{label.id}: attention weight {weight} outside [0,1]"
                )
            _check_span_bounds(
                attention.span,
                text,
                label_id=label.id,
                context="attention",
                errors=errors,
            )

        if label.labels.explosion is not None:
            beat_value = int(label.labels.explosion.beat)
            if allowed_beats and beat_value not in allowed_beats:
                ordered = ", ".join(str(beat) for beat in sorted(allowed_beats))
                errors.append(
                    f"{label.id}: explosion beat {beat_value} not in allowed set {{{ordered}}}"
                )

    if errors and errors_as == "raise":
        message = "\n".join(errors)
        raise ValueError(f"Gold corpus validation failed:\n{message}")

    return errors, warnings_out


def validate_blend_rules(
    rules: BlendRules,
    frames: FrameBank,
    schemas: SchemaBank,
    metaphors: MetaphorBank,
) -> None:
    """Validate the blending rule book against the loaded bible assets."""

    errors: List[str] = []

    schema_ids = {schema.id for schema in schemas.schemas}
    metaphor_map = {metaphor.id: metaphor for metaphor in metaphors.metaphors}
    frame_ids = {frame.id for frame in frames.frames}
    bipolar_ids = {mid for mid, item in metaphor_map.items() if item.type == "bipolar"}

    vital_ids: Set[str] = set()
    for relation in rules.vital_relations:
        if relation.id in vital_ids:
            errors.append(f"duplicate vital relation id: {relation.id}")
        vital_ids.add(relation.id)
        if not relation.definition.strip():
            errors.append(f"vital relation {relation.id} must define a description")

    operator_ids: Set[str] = set()
    for operator in rules.operators:
        if operator.id in operator_ids:
            errors.append(f"duplicate operator id: {operator.id}")
        operator_ids.add(operator.id)
        if not 0.0 <= float(operator.cost) <= 1.0:
            errors.append(f"operator {operator.id} cost {operator.cost} outside [0,1]")
        for relation_id in operator.allowed_relations:
            if relation_id not in vital_ids:
                errors.append(
                    f"operator {operator.id} allowed_relations references unknown {relation_id}"
                )
        for relation_id in operator.disallowed_relations:
            if relation_id not in vital_ids:
                errors.append(
                    f"operator {operator.id} disallowed_relations references unknown {relation_id}"
                )

    mapping = rules.counterpart_mapping
    for relation_id in mapping.priority:
        if relation_id not in vital_ids:
            errors.append(
                f"counterpart_mapping.priority references unknown vital relation {relation_id}"
            )

    prefs = rules.compression_preferences
    for relation_id in prefs.allow + prefs.prefer + prefs.disallow:
        if relation_id not in vital_ids:
            errors.append(
                f"compression_preferences references unknown vital relation {relation_id}"
            )

    role_tokens: Set[str] = set()
    for entry in mapping.role_alignment.allow + mapping.role_alignment.disallow:
        if "↔" in entry:
            left, right = entry.split("↔", 1)
            role_tokens.add(left.strip())
            role_tokens.add(right.strip())

    attribute_tokens = {token.strip() for token in mapping.attribute_alignment.allow}
    allowed_prefer_relations = vital_ids | role_tokens | attribute_tokens

    constraints = rules.constraints
    if constraints.max_blend_depth < 1:
        errors.append("constraints.max_blend_depth must be >= 1")
    if constraints.max_ops_per_blend < 1:
        errors.append("constraints.max_ops_per_blend must be >= 1")
    if constraints.max_active_axes < 0:
        errors.append("constraints.max_active_axes must be >= 0")

    def _validate_pairs(name: str, pairs: List[List[str]], valid: Set[str]) -> None:
        for index, pair in enumerate(pairs):
            if len(pair) != 2:
                errors.append(f"{name}[{index}] must include exactly two identifiers")
                continue
            left, right = pair
            for side, identifier in (("left", left), ("right", right)):
                if identifier not in valid:
                    errors.append(
                        f"{name}[{index}].{side} references unknown id {identifier}"
                    )

    _validate_pairs("constraints.banned_schema_pairs", constraints.banned_schema_pairs, schema_ids)
    _validate_pairs(
        "constraints.banned_metaphor_pairs",
        constraints.banned_metaphor_pairs,
        set(metaphor_map),
    )
    _validate_pairs("constraints.banned_frame_pairs", constraints.banned_frame_pairs, frame_ids)

    for metaphor_id in constraints.polar_conflicts:
        if metaphor_id not in bipolar_ids:
            errors.append(
                f"constraints.polar_conflicts references non-bipolar metaphor {metaphor_id}"
            )

    for frame_id, override in rules.frame_overrides.items():
        if frame_id not in frame_ids:
            errors.append(f"frame_overrides references unknown frame {frame_id}")
        if override.frame_id and override.frame_id != frame_id:
            errors.append(
                f"frame_overrides[{frame_id}] frame_id mismatch: {override.frame_id}"
            )
        if (
            override.max_ops_per_blend is not None
            and override.max_ops_per_blend < 1
        ):
            errors.append(
                f"frame_overrides[{frame_id}].max_ops_per_blend must be >= 1"
            )
        if (
            override.max_ops_per_blend is not None
            and override.max_ops_per_blend > constraints.max_ops_per_blend
        ):
            errors.append(
                f"frame_overrides[{frame_id}].max_ops_per_blend exceeds global limit"
            )
        for op_id in override.disallowed_operators + override.operator_whitelist:
            if op_id not in operator_ids:
                errors.append(
                    f"frame_overrides[{frame_id}] references unknown operator {op_id}"
                )
        for relation_id in override.prefer_relations:
            if relation_id not in allowed_prefer_relations:
                errors.append(
                    f"frame_overrides[{frame_id}] prefer_relations includes unknown {relation_id}"
                )
        for op_id in override.operator_cost_adjust:
            if op_id not in operator_ids:
                errors.append(
                    f"frame_overrides[{frame_id}].operator_cost_adjust references unknown operator {op_id}"
                )

    scoring = rules.scoring
    cost_keys = set(scoring.operator_costs)
    for op_id, value in scoring.operator_costs.items():
        if op_id not in operator_ids:
            errors.append(f"scoring.operator_costs references unknown operator {op_id}")
        if not 0.0 <= float(value) <= 1.0:
            errors.append(
                f"scoring.operator_costs[{op_id}] {value} outside [0,1]"
            )
    missing_costs = operator_ids - cost_keys
    if missing_costs:
        errors.append(
            f"scoring.operator_costs missing entries for operators: {sorted(missing_costs)}"
        )

    for key, value in scoring.penalty.items():
        if not 0.0 <= float(value) <= 1.0:
            errors.append(f"scoring.penalty[{key}] {value} outside [0,1]")

    for key, value in scoring.reward.items():
        if not 0.0 <= float(value) <= 1.0:
            errors.append(f"scoring.reward[{key}] {value} outside [0,1]")

    if not 0.0 <= float(scoring.accept_threshold) <= 1.0:
        errors.append(
            f"scoring.accept_threshold {scoring.accept_threshold} outside [0,1]"
        )

    if errors:
        joined = "\n".join(errors)
        raise ValueError(f"Blend rules validation failed:\n{joined}")
