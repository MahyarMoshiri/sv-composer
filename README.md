# SV Composer (Foundation)

PAIR-driven foundation for a world-aware poetic generator.

## Quickstart
```bash
poetry install
poetry run uvicorn sv_api.main:app --reload
```

### (No Poetry) Local quickstart
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r dev-requirements.txt

# CLI (no Poetry):
python -m sv_sdk.cli schemas validate
python -m sv_sdk.cli schemas stats

# Run API:
uvicorn sv_api.main:app --reload

# Tests:
pytest -q --cov
```

## Endpoints

- `GET /status`
- `GET /openapi.json`
- `GET /health`
- `GET /bible/schemas` (optional `id`, `validate`, `source` filters)
- `GET /bible/schemas/compat`
- `GET /bible/metaphors` (optional validation)
- `GET /bible/frames`
- `GET /bible/blend_rules`
- `GET /gold/stats`
- `GET /bible/schemas/lexicon`
- `POST /retrieval/search`
- `POST /compose` (+ `/compose/plan`, `/compose/beat` helpers)
- `POST /blend`
- `POST /generate`
- `POST /evaluate`
- `POST /evaluate/batch`
- `POST /eval/framecheck`
- `POST /control/expectation`
- `POST /control/viewpoint`
- `POST /control/attention`

## Modules

- **P1 — Image-Schema Bank**: [docs/p1-image-schemas.md](docs/p1-image-schemas.md)
- **P2 — Viewpoint & Attention**: [docs/p2-viewpoint.md](docs/p2-viewpoint.md)
- **P3 — Metaphor & Explosion Controller**: [docs/p3-metaphor-explosion.md](docs/p3-metaphor-explosion.md)
- **P4 — Frames & Coherence**: [docs/p4-frames.md](docs/p4-frames.md)
- **P5 — Mental Spaces & Constrained Blending**: [docs/p5-blending.md](docs/p5-blending.md)
- **P6 — Gold Corpus How-To**: [docs/p6-gold.md](docs/p6-gold.md)
- **P7 — RAG Controller & Composer**: [docs/p7-rag-compose.md](docs/p7-rag-compose.md)
- **P8 — Generation Orchestrator**: [docs/p8-generate.md](docs/p8-generate.md)
- **P9 — Evaluator**: [docs/p9-evaluator.md](docs/p9-evaluator.md)
- **P10 — SDK & API**: [docs/p10-sdk-api.md](docs/p10-sdk-api.md)
- **P11 — LLM Harness & Integration**: [docs/p11-llm-harness.md](docs/p11-llm-harness.md)

## Dev
```bash
poetry run pre-commit install
poetry run pytest -q
```

## LLM Configuration

The `/generate` endpoint uses OpenAI Chat Completions (`gpt-5` by default) unless you opt out.

- Set `OPENAI_API_KEY` to enable live generation. Optional overrides:
  - `SV_OPENAI_MODEL` (default `gpt-5`)
  - `SV_OPENAI_TEMPERATURE` (default `0.7`)
  - `SV_OPENAI_TIMEOUT` (default `20` seconds)
- `SV_LLM_DEFAULT` controls the default harness (`openai` or `echo`).
- `SV_OFFLINE=1` forces the deterministic `EchoLLM` stub (used automatically if no API key or the OpenAI SDK is missing). When online mode fails during the first call, the harness also downgrades to `EchoLLM` for the rest of the process.
- You can still plug in custom providers via `SV_LLM_IMPL=/path/to/module` and an optional `SV_LLM_FACTORY` (defaults to `create_llm`).
