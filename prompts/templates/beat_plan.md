
Create a concise 6-beat intent plan that fits the given frame, active selections, and thresholds. Do not write poetry; write goals.

### Inputs
- Frame: {{frame.id}} — {{frame.definition}}
- Active schemas: {{active.schemas}}
- Active metaphors: {{active.metaphors}}
- Poles: {{poles}}
- Beats config: {{beats}}          # includes names, expectation_target per beat
- Thresholds: {{thresholds}}

### Planning Guidance
- Each beat should have an **intent** (what changes), a **focus** (schemas/metaphors), and **constraints** (what to avoid or include).
- Ensure the **turn** beat hosts the semantic explosion; earlier beats prepare it.
- No new metaphors after **settle**; keep max 2 schema foci per beat.

### Output Contract (JSON)
{
  "beats": [
    {"name":"hook", "intent":"...", "focus":{"schemas":["..."], "metaphors":["..."]}, "expectation_target": 0.2},
    {"name":"setup", "intent":"...", "focus":{"schemas":["..."], "metaphors":["..."]}, "expectation_target": 0.4},
    {"name":"development", "intent":"...", "focus":{"schemas":["..."], "metaphors":["..."]}, "expectation_target": 0.6},
    {"name":"turn", "intent":"...", "focus":{"schemas":["..."], "metaphors":["..."]}, "expectation_target": 0.85},
    {"name":"reveal", "intent":"...", "focus":{"schemas":["..."], "metaphors":["..."]}, "expectation_target": 0.9},
    {"name":"settle", "intent":"...", "focus":{"schemas":["..."], "metaphors":["..."]}, "expectation_target": 1.0}
  ]
}
Return **only** JSON.
