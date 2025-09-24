# P10 SDK API

This document describes the read-only API surface shipped with the P10 release. All endpoints return JSON envelopes of the form `{ "ok": bool, "data": object, "warnings": [], "errors": [] }` unless otherwise noted.

## Core Endpoints

| Endpoint | Description |
| --- | --- |
| `GET /status` | Process health, SDK version (`sv_sdk.__version__`), bible file hashes, and runtime metadata. |
| `GET /openapi.json` | FastAPI-generated OpenAPI schema for the entire service. |
| `GET /bible/schemas` | Retrieve curated schemas; supports `id`, `validate`, and `source` (`current`/`normalized`) query parameters. |
| `GET /bible/schemas/compat` | Compatibility adjacency list keyed by schema ID. |
| `GET /bible/metaphors` | Retrieve curated metaphors; supports `id` and `validate` query parameters. |
| `GET /bible/frames` | Retrieve curated frames, optionally filtered by `id`. |
| `GET /bible/blend_rules` | Retrieve blend rulebook with optional validation toggle. |
| `GET /gold/stats` | Aggregated statistics for the gold labelled corpus with SHA finger-printing. |
| `POST /retrieval/search` | Hash embedder backed RAG retrieval with trace metadata. |
| `POST /compose` | Compose a scene that stitches retrieved assets and schema recommendations. |
| `POST /generate` | Generation endpoint invoking the default composition stack. |
| `POST /evaluate` | Deterministic evaluator returning scoring details. |
| `POST /plan/shots` | (Optional) Generate coarse shot plans when planner is enabled. |

## SDK Surface

The `sv_sdk` package re-exports safe loader utilities for bible content, beats configuration, and gold corpus access. Import helpers directly from the top-level package:

```python
from sv_sdk import (
    __version__,
    load_schema_bank,
    load_metaphor_bank,
    load_frame_bank,
    load_blend_rules,
    load_beats_config,
    load_bible_version,
    load_gold_jsonl,
    compute_gold_stats,
    bible_versions,
)
```

`sv_sdk.versioning.bible_versions()` compiles `{version, sha256, path}` metadata for schemas, metaphors, frames, blend rules, beats, thresholds, and gold labels. The `/status` endpoint and startup logs both reuse this helper so downstream services can detect drift across deployments.

## CORS Toggle

Set `SV_API_ENABLE_CORS=true` (or `1`, `yes`, `on`) to enable permissive CORS headers. The toggle defaults to `off`, which matches FastAPI TestClient expectations in the automated suite.

## LLM Defaults & Overrides

- Runtime defaults to the built-in OpenAI provider (`gpt-5`).
- Configure the harness with:
  - `OPENAI_API_KEY` (required online)
  - `SV_OPENAI_MODEL`, `SV_OPENAI_TEMPERATURE`, `SV_OPENAI_TIMEOUT`
  - `SV_LLM_DEFAULT` (`openai` or `echo`)
  - `SV_OFFLINE=1` to force the deterministic `EchoLLM` stub (tests use this automatically when no key is present).
- `SV_LLM_IMPL`/`SV_LLM_FACTORY` continue to support custom providers; failures fall back to `EchoLLM`.

## Release Checklist

- Update `CHANGELOG.md` with release notes.
- Bump `sv_sdk.__version__` and retag the repository (`git tag v0.1.0`).
- Verify `/openapi.json` resolves and documentation reflects any new endpoints.
