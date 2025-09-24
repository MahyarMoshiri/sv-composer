# BEAT: {{beat.name}}
Goal: {{beat.goal}}
Constraints: {{beat.constraints}}
Length: {{beat.min_chars}}–{{beat.max_chars}} chars
Expectation target: {{beat.expectation_target}}
Required tokens (optional): {{must_use}}
Prohibited tokens (optional): {{ban_words}}
Style rules: see appended style_rules.md

**Write 1–2 lines** that satisfy the goal and constraints. Keep within the character range. Do not include explanations, headings, or numbering.

Inputs:
- {{beat.name}}, {{beat.goal}}, {{beat.constraints}}, {{beat.min_chars}}, {{beat.max_chars}}, {{beat.expectation_target}}, {{must_use}}, {{ban_words}}

# Output Contract
Return only the lines of the beat, no extra text.
