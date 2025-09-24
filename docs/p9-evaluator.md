# P9 — Evaluator Loop

The P9 milestone introduces a deterministic scoring loop that validates composed pieces without calling an LLM. The evaluator consumes the final piece, the composer trace, configuration thresholds, and the schema/metaphor/frame banks to produce a stable pass/fail result together with diagnostics.

## Metrics (0..1)
- **frame_fit** – wraps `sv_eval.framecheck.check_frame` over the trace’s active selections against the resolved frame. A clean pass maps to `1.0`; violations subtract weight.
- **schema_cov** – fraction of active schemas that surface in the piece. We reuse the lexicon matcher (`sv_control.lexicon.match_lemmas`) as a proxy for lexical coverage.
- **metaphor_diversity** – Shannon-style entropy of selected metaphors across beats, normalised to `[0,1]`.
- **attention_discipline** – top span concentration from `sv_control.attention.attention_weights`. Higher focus on the leading spans yields higher discipline.
- **explosion_timing** – expectation value at the TURN beat (`trace.curve_after`) scored against `thresholds.explosion_timing_range`.

## Penalties & Criticals
- **Penalties** – Config-driven deductions (e.g. `frame_violation`, `over_length`, `banned_pair`, `missing_trace`, `weak_turn`). Totals clamp at `≤0.90` before subtracting from the weighted score.
- **Critical Violations** – Immediate failure switches (`disallowed_content`, `explosion_outside_turn`, `empty_output`). These bypass the weighted score even when metrics look healthy.

## Score & Decision
1. Compute `score_pre_penalty = Σ(weights[k] * metric[k])` with frame/metaphor overrides applied.
2. Subtract penalties to obtain `score_final` (clamped to `[0,1]`).
3. Evaluate the configured `acceptance_rule` with helper symbols (`score`, `total_penalty`, `floors_ok`, `any_critical`, `in_range(...)`, etc.).
4. Return a structured payload:
   ```json
   {
     "pass": true,
     "score_pre_penalty": 0.78,
     "score_final": 0.72,
     "total_penalty": 0.06,
     "metrics": {...},
     "penalties_applied": [{"code": "over_length", "value": 0.15}],
     "critical_violations": [],
     "reasons": ["metric schema_cov below min 0.6"],
     "trace_echo": {"turn_index": 3, "explosion_value": 0.88}
   }
   ```

## Interfaces
### Python
`sv_eval.evaluator.evaluate(piece, trace, thresholds, banks)` – pure function suitable for pipelines/tests.

### API
- `POST /evaluate` → `{ ok, data, warnings, errors }`
- `POST /evaluate/batch` → envelopes per `id`, with partial failures reported in `errors`.

### CLI
```
sv evaluate piece.txt --trace trace.json
```
Prints pass/fail, weighted score, metrics summary, penalties, and criticals for quick smoke checks.

## Testing
- `pytest tests/test_evaluator_core.py -q`
- `pytest tests/test_evaluate_api.py -q`

Passing these suites ensures the evaluator loop is deterministic, honours configuration thresholds, and surfaces actionable diagnostics through the API and CLI.
