# P6 — Gold Corpus How-To

## File Layout & Encoding

`data/gold/labels.jsonl` stores one curated example per line as UTF-8 JSON. Text and metadata are normalized to NFC so accent-insensitive comparisons stay stable. Spans use the `[start, end)` convention with character offsets into the normalized `text` field; end indices are exclusive.

Each entry looks like:

```json
{
  "id": "gold_0001",
  "lang": "en",
  "text": "they cross the narrow bridge",
  "labels": {
    "schemas": [{ "id": "path", "spans": [[5, 10], [22, 28]] }],
    "metaphors": [{ "id": "life_is_travel", "spans": [[0, 4]] }],
    "frame": { "id": "journey" },
    "viewpoint": { "person": "3rd", "tense": "present", "distance": "medium" },
    "attention": [{ "span": [5, 10], "w": 0.6 }],
    "explosion": { "beat": 4, "confidence": 0.9 }
  },
  "provenance": {
    "curator": "Mahyar",
    "source": "curated",
    "license": "CC-BY",
    "confidence": 0.9,
    "notes": "optional annotation notes"
  }
}
```

### Span Rules

- Spans must satisfy `0 ≤ start < end ≤ len(text)` after NFC normalization.
- Duplicate spans inside the same annotation are deduplicated during loading.
- Attention spans mirror the annotation rule; weights must stay within `[0, 1]`.

### Coverage Targets

- `lang` is limited to `en` and `fa` to match the bilingual banks.
- Schema, metaphor, and frame ids must reference curated bible assets.
- Bipolar metaphors (`type: bipolar`) may carry an explicit `pole`; primary metaphors must leave it unset.
- `explosion.beat` follows `config/beats.yml` ordering (currently beats 1–6).

## CLI Workflows

Two Typer commands streamline validation and inspection:

```
python -m sv_sdk.cli gold validate [--path PATH]
python -m sv_sdk.cli gold stats [--path PATH]
```

`gold validate` loads the corpus, bible banks, and beat config, logging the bible version plus a SHA-256 digest of the JSONL. It reports total items, warnings, and blocking errors. Warnings surface viewpoint mismatches when no explicit cue is present; errors flag span bounds, unknown ids, weight/beat violations, or duplicate example ids. The command exits with code `1` if any errors are encountered.

`gold stats` prints high-level coverage metrics:

- totals per language, frame, schema, and metaphor
- histogram of `explosion.beat`
- average attention weight and annotated-span count
- percentage of metaphor annotations with an explicit pole value

## API Surface

The optional FastAPI router mounts `GET /gold/stats`. It returns the same aggregate payload as the CLI `stats` command (no raw texts) alongside the corpus SHA-256 and bible version header. Use it for monitoring dashboards or regression alerts without exposing example content.

## Acceptance & Regression

The Definition of Done for P6:

1. `python -m sv_sdk.cli gold validate`
2. `python -m sv_sdk.cli gold stats`
3. `pytest -q tests/test_gold_loader_validate.py tests/test_gold_stats.py`
4. (optional) `uvicorn sv_api.main:app --reload &` then `curl -s localhost:8000/gold/stats | jq`

Tests ship with `tests/fixtures/gold_small.jsonl`, ensuring loader normalization, validator checks (bad spans, unknown ids, invalid beats), and stats aggregation remain stable.
