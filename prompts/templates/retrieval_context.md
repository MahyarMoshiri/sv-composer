# WORLD CONTEXT (Read-Only)
Frame: {{frame.id}} — {{frame.definition}}
Required schemas: {{frame.required_schemas}}
Allowed metaphors: {{frame.allowed_metaphors}}
Viewpoint defaults: {{frame.viewpoint_defaults}}
Gates allowed: {{frame.gates_allowed}}
Motif hints: {{frame.motif_hints}}

# ACTIVE SELECTIONS
Active schemas: {{active.schemas}}
Active metaphors: {{active.metaphors}}
Bipolar poles (if any): {{active.poles}}
Viewpoint hint: {{viewpoint}}
Attention focus: {{attention}}
Expectation so far (0..1): {{expectation}}

# EXEMPLARS (Few-shot)
{{#each exemplars}}
- {{this.lang}}: {{this.text}}
{{/each}}

**Instruction**: Use only the items above. If something is not present here, do not invent it.

Inputs:
- {{frame.*}}, {{active.schemas}}, {{active.metaphors}}, {{active.poles}}, {{viewpoint}}, {{attention}}, {{expectation}}, {{exemplars}}
# Output Contract
Render exactly as above; no additions or explanations.
