# P12 Style Enrich — Strict JSON Response Schema

The assistant **must return STRICT JSON** with the following keys and no extras. All values are short, declarative fragments.

```json
{
  "camera": "string",
  "framing": "string",
  "composition": "string",
  "lens": "string",
  "movement": "string",
  "lighting": "string",
  "color": "string",
  "motion": "string",
  "audio": "string",
  "transition_in": "string",
  "transition_out": "string",
  "negative_prompt": "string",
  "notes_short": "string"
}
```

## Field rules

* **camera**: ≤ 14 words. Movement direction or setup, e.g., “slow push-in from doorway”.
* **framing**: ≤ 10 words. Shot size + vantage, e.g., “medium-wide from threshold”.
* **composition**: ≤ 10 words. Spatial arrangement, e.g., “balanced thirds, doorway framing”.
* **lens**: ≤ 10 words. Prime/zoom and focal length, e.g., “35mm”.
* **movement**: ≤ 10 words. Dolly/track/handheld specifics, e.g., “tracking along axis”.
* **lighting**: ≤ 14 words. Key style + accents, e.g., “low-key dusk, soft window rim”.
* **color**: ≤ 14 words. Palette hints, e.g., “muted cools with warm edge glow”.
* **motion**: ≤ 14 words. Subject or environmental motion, e.g., “gentle curtain flutter”.
* **audio**: ≤ 10 words. Ambience/foley/music cue, e.g., “room tone, soft hush”.
* **transition_in / transition_out**: ≤ 10 words. One of: cut, dissolve, match-cut, hard cut, whip.
* **negative_prompt**: comma-separated bans; must include tokens_ban from USER.
* **notes_short**: optional; ≤ 16 words; no meta text.

## Validation

* No chain-of-thought, explanations, or extra keys.
* Never echo banned tokens in positive fields.
* Keep each scene within its duration (5s/10s) — avoid multi-location arcs.
* Don’t invent proper nouns, brands, or copyrighted characters.
