# SV Composer (Foundation)

PAIR-driven foundation for a world-aware poetic generator.

## Quickstart
```bash
poetry install
poetry run uvicorn sv_api.main:app --reload
```

## Endpoints

- `GET /health`
- `GET /bible/schemas` (full schema bank, optional `?id=` filter)
- `GET /bible/schemas/compat` (coactivation adjacency list)
- `GET /bible/schemas/lexicon` (lexicon matches for a text snippet)
- `POST /compose` → { text, trace } (stub)
- `POST /evaluate` → { scores, pass } (stub)

## Modules

- **P1 — Image-Schema Bank**: [docs/p1-image-schemas.md](docs/p1-image-schemas.md)

## Dev
```bash
poetry run pre-commit install
poetry run pytest -q
```
