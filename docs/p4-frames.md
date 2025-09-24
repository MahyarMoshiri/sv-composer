# P4 — Frames & Coherence

## Frame Bible Structure
- `version`: semantic version of the frame release shipped in `bible/frames.yml`.
- `frames[]`: list of frame records; each record carries the following fields.
  - `id`: stable identifier referenced by composer, trace, and downstream tooling.
  - `definition`: short description of the situational gestalt (warned if longer than 160 characters).
  - `core_roles[]` / `optional_roles[]`: canonical participants; `role_notes{}` optionally adds curator commentary.
  - `allowed_schemas[]`, `required_schemas[]`, `disallowed_schemas[]`: schema constraints enforced by the validator and the coherence checker.
  - `allowed_metaphors[]`, `disallowed_metaphors[]`, `metaphor_bias{}`: metaphor whitelist/blacklist plus weight hints for expectation biasing.
  - `viewpoint_defaults{person, tense, distance}`: narrator defaults used when the prompt offers no explicit cues.
  - `attention_defaults[]`: optional `{role|schema, w}` hints for attention balancing (each weight must be within `[0, 1]`).
  - `gates_allowed[]`: permitted spatial gates for the frame; validated when a curated gate bible is available.
  - `motif_hints[]`: unstructured motif suggestions for prompt builders.
  - `beat_affinity{}`: beat weights (`hook`, `setup`, `development`, `turn`, `reveal`, `settle`, with `hook_out` treated as an alias for `settle`).
  - `examples`: curated text examples, reused from the shared `Examples` model.
  - `provenance`: attribution metadata inherited from the SDK models.

## Example Entry
```yaml
- id: journey
  definition: "Movement from a known source toward a shifting goal along a constrained route."
  core_roles: [traveler, source, path, goal]
  allowed_schemas: [path, boundary, link]
  required_schemas: [path]
  allowed_metaphors: [life_is_travel, memory_is_map]
  viewpoint_defaults: {person: "3rd", tense: "present", distance: "medium"}
  attention_defaults: [{role: traveler, w: 0.5}, {schema: path, w: 0.6}]
  gates_allowed: [bridge, tunnel, stairs, door]
  beat_affinity: {hook: 0.45, setup: 0.6, development: 0.75, turn: 0.55, reveal: 0.45, hook_out: 0.4}
  examples:
    text: ["she follows the thin street toward a name that keeps moving"]
  provenance: {source: "PoemCorpus v0.1 + SV_Extended v0.1", curator: "Mahyar", license: "CC-BY", confidence: 0.86}
```

## Validation Highlights
- Frame identifiers must be unique.
- `required_schemas` must be a subset of `allowed_schemas`.
- Schema and metaphor references must exist in their respective bibles; `metaphor_bias` keys must also be allowed.
- `attention_defaults[].w`, `metaphor_bias`, and `beat_affinity` weights must stay inside `[0, 1]`.
- Gates are checked against `bible/gates.yml` when present (otherwise a warning is surfaced).
- Definitions longer than 160 characters emit warnings to keep curator blurbs concise.

## Coherence Reason Codes
| Code | Meaning |
| --- | --- |
| `FRM_MISSING_REQUIRED_SCHEMA` | Active selection did not include a schema marked as required by the frame. |
| `FRM_DISALLOWED_SCHEMA` | Active schemas violate the frame (explicit blacklist or not in the allowed set). |
| `FRM_DISALLOWED_METAPHOR` | Active metaphors conflict with the frame’s constraints. |
| `FRM_GATE_NOT_ALLOWED` | A gate outside the frame’s whitelist was activated. |
| `FRM_VIEWPOINT_MISMATCH` | The realised viewpoint contradicts the frame defaults without an explicit cue. |
| `FRM_BEAT_AFFINITY_WEAK` | Informational notice: supplied beat is weakly supported (< 0.5 weight or unknown). |

Only the first five codes block `pass=True`; beat affinity notices keep the evaluation informational.

## API Usage
- `GET /bible/frames?id=&validate=` returns `{ ok, data: { summary, frames, warnings? }, errors }`.
  - `summary` includes version, frame count, and role totals.
  - `validate=true` runs `validate_frame_bank` and returns HTTP 422 if invariants fail; warnings (e.g. missing gate bible) are included in the payload when validation succeeds.
  - `id` filters by frame identifier.
- `POST /eval/framecheck` accepts either direct selections or a trace:
  ```json
  {
    "frame_id": "journey",
    "active": {
      "schemas": ["path", "boundary"],
      "metaphors": ["life_is_travel"],
      "gates": ["bridge"],
      "viewpoint": {"person": "3rd", "tense": "present", "distance": "medium"}
    }
  }
  ```
  ```json
  {
    "frame_id": "journey",
    "trace": {
      "selected": {
        "schemas": ["path"],
        "metaphors": ["life_is_travel"],
        "gates": ["bridge"],
        "beats": ["turn"]
      },
      "steps": [{"vp": {"person": "3rd", "tense": "present", "distance": "medium"}}]
    }
  }
  ```
  Both responses return `{ ok, data: { pass, reasons, details }, errors: [] }`. Endpoint logs the frame bible version, requested `frame_id`, reason codes, and the SHA of `bible/frames.yml` for traceability.

## Integration Notes
- **Composer** selects a frame (`frame_id`) and records active schemas/metaphors/gates into its trace; `extract_active_from_trace` reads several common trace shapes (top-level `selected_*` keys or `steps[].vp`).
- **Evaluator** invokes `check_frame` (via the API or directly) to ensure authorial choices respect frame constraints before scoring; only blocking reason codes flip `pass` to `False`.
- **Control surfaces** (viewpoint, attention) reuse the same defaults: when prompts offer no cues, the frame defaults seed viewpoint inference; explicit cues (e.g. `viewpoint.explicit = true`) override without penalty.
- Logging on `/eval/framecheck` makes every coherence decision auditable by tying reason codes back to the shipped frame bible revision.
