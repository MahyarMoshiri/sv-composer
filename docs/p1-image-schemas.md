# P1 — Image-Schema Bank

Image-schemas are recurring, embodied patterns that structure how humans perceive and reason about spatial, temporal, and force relations. They distill sensorimotor experiences into abstract gestalts that can be combined in language, narrative, and visual storytelling. The curated bank encodes each schema with parameters, affective tones, and lexical triggers for downstream tooling.

## Field glossary

- **id**: Stable identifier for the schema entry.
- **title**: Human-readable name of the schema.
- **definition**: Concise description of the embodied pattern.
- **roles**: Salient participants or aspects that define the schema structure.
- **params**: Tunable dimensions, each defined by a `ParamSpec` with bounds or enum values.
- **affect**: Core valence/arousal metrics (plus optional tags) describing experiential tone.
- **lexicon**: Language-specific lexemes with weights in the range `[0, 1]`.
- **coactivate**: Related schema identifiers that frequently co-occur or trigger each other.
- **examples**: Textual and visual vignettes illustrating the schema.
- **provenance**: Metadata documenting source material, curator, license, and confidence.

## How to run validation & stats

```bash
poetry run sv schemas validate
poetry run sv schemas stats
```

## API usage

Fetch the full schema set (with optional filtering):

```bash
curl -s http://localhost:8000/bible/schemas | jq
curl -s "http://localhost:8000/bible/schemas?id=container" | jq
```

Retrieve the coactivation graph adjacency list:

```bash
curl -s http://localhost:8000/bible/schemas/compat | jq
```

Get lexicon-based matches for a text snippet:

```bash
curl -s "http://localhost:8000/bible/schemas/lexicon?lang=en&text=inside%20room" | jq
```
