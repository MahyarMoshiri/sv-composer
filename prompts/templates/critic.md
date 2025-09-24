
Evaluate the candidate lines strictly against the provided World Bible context and the metrics below. Do **not** reveal chain-of-thought; emit only the JSON contract.

### Inputs
- Frame (id & rules): {{frame}}
- Active selections: {{active}}   # schemas, metaphors, poles
- Beat info: {{beat}}             # name, expectation_target
- Candidate (text):
{{candidate}}
- Thresholds: {{thresholds}}      # mirrors config/thresholds.yml

### Checks (define each as pass/fail and short reason)
- frame_fit: Candidate respects frame constraints (required/disallowed schemas, metaphors, gates, viewpoint defaults unless explicit cues override). 
- schema_cov: Realizes targeted schemas (from {{active.schemas}}) in concrete imagery.
- metaphor_coherence: Uses active metaphors consistently; no banned pairs; no new metaphors beyond beat constraints.
- attention_discipline: Focus stays on declared center; avoid drift/overload.
- explosion_timing: Moves expectation toward the target for this beat; if beat is `turn`, ensure the semantic explosion lands here.
- form_limits: Length within beat char bounds; no more than 2 lines; no stage directions.

### Output Contract (JSON)
{
  "pass": true|false,
  "metrics": {
    "frame_fit": 0.0..1.0,
    "schema_cov": 0.0..1.0,
    "metaphor_diversity": 0.0..1.0,     // entropy or simple variety proxy
    "attention_discipline": 0.0..1.0,
    "explosion_timing": 0.0..1.0
  },
  "violations": [
    // stable codes to align with evaluator & framecheck
    "FRM_MISSING_REQUIRED_SCHEMA" | "FRM_DISALLOWED_SCHEMA" | "FRM_DISALLOWED_METAPHOR" |
    "BANNED_PAIR" | "OVER_LENGTH" | "NEW_METAPHOR_NOT_ALLOWED" | "WEAK_TURN" | "VIEWPOINT_DRIFT"
  ],
  "reasons": ["short human-readable bullets"],
  "fix": "one concise, concrete edit the model can apply in a single pass"
}
Return **only** valid JSON. No prose.

