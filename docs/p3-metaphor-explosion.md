# P3 Metaphor & Explosion Controller

## Metaphor Bank
- **Schema**: `MetaphorItem` extends the bible with affect, lexicon, gating, and provenance. Optional fields (`source_schema`, `axis`, `bipolar`, `banned_with`) are preserved for forward compatibility.
- **Loading**: `sv_sdk.loader.load_metaphor_bank()` ingests `bible/metaphors.yml` into a typed `MetaphorBank` while keeping curated data untouched.
- **Validation**: `sv_sdk.validators.validate_metaphor_bank()` enforces unique IDs, weight and valence ranges, gating increments within `[0,1]`, and hard checks that `source_schema`/`coactivate_schemas` align with the schema bible. Preferred frames are soft-checked: unknown IDs surface as warnings, file absence logs a warning.

## Expectation Engine
- **Base Curve**: `sv_control.expectation.build_curve()` converts the requested beat list into a monotonic 0→1 trajectory using `config/beats.yml` (`beat_order` + `expectation_targets`). Missing beats fall back to an even ramp.
- **Bias Application**: `apply_metaphor_bias()` looks up gating info for active metaphors, adds `expectation_increment` to the configured `beats_bias`, clamps to `1.0`, and restores monotonicity. Both the untouched and biased curves are retained.
- **Explosion Detection**: `find_explosion_step()` scans for the first value ≥ threshold (from `config/thresholds.yml.explosion_timing_range`). Reasons are `within_window`, `before_window`, `after_window`, or `threshold_not_reached`.
- **Trace**: `compute_expectation_trace()` returns `{beats, curve_before, curve_after, active_metaphors, fired_step}`; helpers expose defaults, the metaphor bible SHA, and backwards-compatible wrappers (`expectation_curve`, `should_explode`).

## APIs
- **GET `/bible/metaphors`**: Envelope `{summary, metaphors, warnings?}` with optional `id` filter. `validate=true` runs the validator (422 on failure, warnings returned when soft checks trigger).
- **POST `/control/expectation`**: Body `{active_metaphors, poles?, beats?, base?}`. Response envelope contains `{beats, curve_before, curve_after, fire, active_metaphors, poles}`. When beats are omitted the configured default is used.

## Logging
- `/control/expectation` logs `bible.version`, `active_metaphors`, `fire_beat_index`, and the SHA256 of `bible/metaphors.yml` via `metaphor_bank_sha()`.

## Validation Checklist
- `pytest tests/test_metaphor_validation.py -q`
- `pytest tests/test_expectation_controller.py -q`
- `pytest tests/test_metaphors_api.py -q`
- Manual smoke: run the API, hit the new endpoints, inspect logs and validation warnings.
