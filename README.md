# SV Composer (Foundation)

PAIR-driven foundation for a world-aware poetic generator.

## Quickstart
```bash
poetry install
poetry run uvicorn sv_api.main:app --reload
```

## Endpoints

- `GET /health`
- `GET /bible/{section}` (section ∈ schemas|frames|metaphors)
- `POST /compose` → { text, trace } (stub)
- `POST /evaluate` → { scores, pass } (stub)

## Dev
```bash
poetry run pre-commit install
poetry run pytest -q
```
