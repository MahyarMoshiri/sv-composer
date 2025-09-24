# P5 — Mental Spaces & Constrained Blending

## Overview

The P5 milestone introduces a deterministic blending workflow that sits on top of the curated rulebook in `bible/blend_rules.yml`. Two minimal input spaces are derived from the caller's selection (`SceneActive`), mapped via the counter-part priorities declared in the rulebook, and composed through a constrained operator set. Everything is auditable: every mapping, operator choice, reward and penalty is recorded for downstream inspection.

Key ingredients:

- **Spaces**: `build_spaces` extracts space A (schemas, gates, optional frame) and space B (metaphors/poles). Inputs are deduplicated to keep ordering stable.
- **Vital relations**: Declared in the bible; used to prioritise mappings and vet operator eligibility.
- **Operators**: `apply_operators` enforces global and per-frame limits, cost adjustments, and operator whitelists. Safe operators are preferred, with deterministic tie-breaking.
- **Scoring**: Rewards (`frame_compat`, `schema_alignment`, `metaphor_alignment`, `minimality`, `novelty_cap`) are combined and operator costs are subtracted. Penalties (banned pairs, depth overflow, frame incompatibility, polar conflicts) are applied unless an explosion override permits them.

## Rule Loading & Validation

- `sv_sdk.loader.load_blend_rules()` returns a `BlendRules` model mirroring the YAML bible.
- `sv_sdk.validators.validate_blend_rules(rules, frames, schemas, metaphors)` enforces:
  - Unique vital-relation/operator IDs and numeric ranges in `[0,1]`.
  - Cross references (`allowed_relations`, compression prefs, overrides, polar conflicts) against the banks.
  - Frame overrides that only touch real frames/operators and stay within global limits.
  - Banned schema/metaphor/frame pairs referencing existing IDs.
  - Polar conflict axes that target bipolar metaphors.

All violations raise `ValueError` with a consolidated message, allowing the `/bible/blend_rules` endpoint to fail fast when `validate=true`.

## Engine Surface

`sv_blend.blend` exposes:

- `SceneActive`: dataclass input (schemas, metaphors, poles, gates, frame, explosion flag).
- `build_spaces(active) -> (Space, Space)`: prepares the two input spaces.
- `propose_mappings(A, B, rules) -> list[Mapping]`: honours allow/disallow lists and prioritises vital relations.
- `apply_operators(mappings, rules, frame_override) -> list[BlendStep]`: respects safety, max-ops, and cost adjustments.
- `blend(active, rules) -> dict`: returns `{accepted, score_pre_penalty, score_final, decisions, audit}`.

The audit block contains:

- `spaces`: deduped selections for each space.
- `mappings`: chosen alignments (left/right, relation, rationale).
- `operators`: the ordered operator plan with per-step costs (post overrides).
- `costs`: summed operator cost.
- `rewards`: metric → `{metric, weight, contribution}`.
- `penalties`: applied penalties with reasons/weights.
- `thresholds`: accept threshold, max depth, max ops.
- `flags`: explosion status.

## API Endpoints

- **GET `/bible/blend_rules?validate=true`**
  - Loads rules, optionally validates against frames/schemas/metaphors.
  - Returns `{ ok, data: { summary, rules }, warnings, errors }` or `422` with validation errors.

- **POST `/blend`**
  - Body:

    ```json
    {
      "frame_id": "journey",
      "active": {
        "schemas": ["path", "boundary"],
        "metaphors": ["life_is_travel", "raw_cooked"],
        "poles": {"raw_cooked": "raw"},
        "gates": ["bridge"]
      },
      "explosion_fired": false
    }
    ```

  - Response:

    ```json
    {
      "ok": true,
      "warnings": [],
      "errors": [],
      "data": {
        "accepted": true,
        "score_pre_penalty": 1.0,
        "score_final": 1.0,
        "decisions": {"operators": ["projection", "composition"], "mappings": 2},
        "audit": { ... }
      }
    }
    ```

  - When polar conflicts occur, the engine emits a `polar_conflict:*` penalty and the API sets `warnings=["penalties_applied"]`. If `explosion_fired=true` and the rulebook allows it, the penalty is skipped.

## Manual Checks

```
pytest tests/test_blend_rules_validation.py -q
pytest tests/test_blend_engine_safe.py tests/test_blend_engine_unsafe.py -q
pytest tests/test_blend_api.py -q

uvicorn sv_api.main:app --reload &
curl -s 'localhost:8000/bible/blend_rules?validate=true' | jq '.ok,.data.summary'
curl -s 'localhost:8000/blend' -H 'content-type: application/json' \
  -d '{"frame_id":"journey","active":{"schemas":["path","boundary"],"metaphors":["life_is_travel","raw_cooked"],"poles":{"raw_cooked":"raw"},"gates":["bridge"]},"explosion_fired":false}' | jq
```

These steps mirror the Definition of Done: rules load & validate, the engine produces deterministic audits, the API surfaces the decisions, and documentation covers every moving part.
