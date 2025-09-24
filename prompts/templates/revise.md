
Revise the candidate minimally to satisfy the critic. Keep meaning and style; prefer **surgical edits** over rewrites.

### Inputs
- Candidate:
{{candidate}}
- Critic JSON (pass=false):
{{critic_json}}
- Frame & constraints:
{{frame}}
- Beat & limits: {{beat}}
- Style rules: (assumed loaded separately)

### Revision Rules
- Only edit tokens necessary to flip the failing checks to pass.
- Enforce beat character bounds ({{beat.min_chars}}–{{beat.max_chars}}) and max 2 lines.
- Do **not** introduce new metaphors not present in {{active.metaphors}}.
- Respect frame required/disallowed schemas and gates.
- Keep viewpoint consistent unless explicit cues demand otherwise.

### Output Contract
Return **only** the revised lines (1–2 lines), with no commentary, JSON, or extra text.
