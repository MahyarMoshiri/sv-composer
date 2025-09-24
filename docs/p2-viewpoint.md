# P2 — Viewpoint & Attention

This module infers simple narrator viewpoint hints and extracts high-salience schema cues from text. All rules are declarative and live in `config/viewpoint_rules.yml`, keeping behaviour fully deterministic.

## Inferred Signals
- **Person**: detects first-person cues (`I`, `we`), second-person cues (`you`, direct imperatives), otherwise defaults to third-person.
- **Tense**: past-tense verbs (`walked`, `crossed`), past adverbs (`yesterday`, `ago`), or Farsi past cues trigger `past`; otherwise `present`.
- **Distance**: container/boundary or body-proximate lexemes (`inside`, `room`, `hands`) yield `close`; horizon/landscape terms (`horizon`, `mountain`) yield `far`; otherwise `medium`.

Explicit lexical cues always override frame defaults. When no cues are found, optional frame defaults from `bible/frames.yml` (via `viewpoint_defaults`) are applied next, followed by the per-frame and global fallbacks defined in `config/viewpoint_rules.yml`.

## Attention Map
`attention_weights(text, lang)` sums schema lexicon weights (from P1) for all lexemes found in the text and returns the top matches. Each peak contains:

```json
{ "token": "container", "w": 0.9 }
```

The list is stable for a given input and language, and never depends on external services.

## API Usage

### POST `/control/viewpoint`
```json
{
  "prompt": "inside the room we breathed softly",
  "frame_id": "journey",
  "lang": "en"
}
```
Response:
```json
{
  "ok": true,
  "data": {
    "viewpoint": {"person": "1st", "tense": "present", "distance": "close"},
    "attention": [{"token": "container", "w": 1.5}]
  },
  "errors": []
}
```
API logs the active Bible version, provided frame, and the inferred hint.

### POST `/control/attention`
```json
{
  "text": "across the bridge at night",
  "lang": "en"
}
```
Response envelope mirrors the viewpoint endpoint, with `data.attention` holding the ordered peaks.

## Examples
- `I walk across the bridge` → person `1st`, distance `close`, path/link attention peaks.
- `Yesterday they watched the horizon` → tense `past`, distance `far`.
- With `frame_id="journey"` and no explicit cues, defaults from the frame are applied.

## Extensibility
- Cue lexicons and fallbacks are maintained in YAML (`config/viewpoint_rules.yml`). Adjusting weights or adding new languages only requires editing the config file and reloading the service.
- Frame-specific defaults remain in `bible/frames.yml` (`viewpoint_defaults`) and win over config fallbacks when present.
