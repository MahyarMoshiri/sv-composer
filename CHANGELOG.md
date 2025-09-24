# Changelog

## [0.1.0] - 2025-09-21
### Added
- World Bible SDK surface (`sv_sdk`): loaders for schemas, metaphors, frames, blend rules, beats, thresholds, gold.
- Deterministic evaluator (`/evaluate`) with metrics/penalties/criticals and CLI `sv evaluate`.
- Retrieval & composition endpoints (`/retrieval/search`, `/compose`, `/generate`) with trace outputs.
- Read-only Bible endpoints (`/bible/*`) and `/gold/stats`.
- `/status` with SDK version and Bible file SHAs.
- OpenAPI available at `/openapi.json`.

### Policy
- Read-only data access via API; updates through curated PRs only.
