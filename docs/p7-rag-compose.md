# P7 — Retrieval Controller & Prompt Composer

This milestone introduces a fully deterministic retrieval stack and beat-oriented prompt composer. The goal is to provide self-contained prompts and traces that downstream LLM agents can execute without accessing network models.

## Retrieval Index

- **Sources**: schemas (`bible/schemas.yml`), metaphors (`bible/metaphors.yml`), frames (`bible/frames.yml`), and gold exemplars (`data/gold/labels.jsonl`).
- **Embedder**: `HashEmbedder` hashes character trigrams into a fixed-length vector (default 4096 dims) and normalises for cosine similarity. No remote model downloads are required for tests.
- **Extensibility**: the embedder protocol (`sv_rag.embeddings.Embedder`) allows swapping in a real model (e.g., `SentenceTransformer`) behind an availability guard without touching the index logic.
- **Index Fields**: each document stores `doc_id`, `kind` (`schema`, `metaphor`, `frame`, `exemplar`), `lang`, `text`, `tags`, `weight`, and a cached embedding. Search is deterministic and filterable by kind or language.

### Retrieval API Example

```bash
curl -s http://localhost:8000/retrieval/search \
  -H 'content-type: application/json' \
  -d '{"query":"bridge at dusk inside room","k":5,"kinds":["schema","frame"]}'
```

Response (abridged):

```json
{
  "ok": true,
  "data": {
    "hits": [
      {"doc_id": "boundary", "kind": "schema", "score": 0.82, "tags": ["boundary"]},
      {"doc_id": "journey", "kind": "frame", "score": 0.76, "tags": ["journey", "path"]}
    ],
    "warnings": []
  }
}
```

## Prompt Composition Pipeline

1. **Active Selection**: `sv_rag.select.select_active` filters top schemas, metaphors, poles, and exemplars for a requested frame, respecting allowed/disallowed lists.
2. **Beat Planning**: `plan_beats` renders `prompts/templates/beat_plan.md` (if present) and validates the returned JSON. When absent, it falls back to `config/beats.yml` goals and expectation targets.
3. **Prompt Rendering**: `compose_piece` renders `system.md`, `retrieval_context.md`, and `compose_beat.md` for every beat, and also packages `critic.md`, `revise.md`, and `compose_final.md` for downstream agents.
4. **Trace Output**: `ComposeTrace` records per-beat selections, tokens, expectation targets, and prompt strings so orchestration layers can audit or replay decisions.

### Compose API Examples

Plan + Active selections:

```bash
curl -s http://localhost:8000/compose/plan \
  -H 'content-type: application/json' \
  -d '{"frame_id":"journey","query":"inside the room at dusk","k":6}' | jq '.data.plan[3]'
```

Full prompt packet + trace:

```bash
curl -s http://localhost:8000/compose \
  -H 'content-type: application/json' \
  -d '{"frame_id":"journey","query":"inside the room at dusk","beats":["hook","setup","development","turn","reveal","settle"]}' \
  | jq '.data.trace.beats[0].beat'
```

Single beat prompt:

```bash
curl -s http://localhost:8000/compose/beat \
  -H 'content-type: application/json' \
  -d '{"frame_id":"journey","beat":"turn","query":"inside the room at dusk","active":{...}}'
```

### Trace & Agent Loop

Downstream LLM agents should:

1. Call `/compose` to obtain per-beat prompts, critic/revise templates, and the trace.
2. For each beat, run the `compose` prompt to draft lines.
3. Feed the candidate into the rendered `critic.md`. If it fails, run `revise.md` once using the critic JSON.
4. After all beats pass, assemble accepted lines with `compose_final.md`.
5. Persist the provided trace for auditing (expectation curves, selections, tokens).

## Logging & Provenance

Startup logs now include:

- `bible_version` plus SHA-256 digests for schemas, metaphors, frames, and blend rules.
- `rag.index.initialized` event with aggregate counts per document kind.
- Embedder identification (`embedder: "hash"`) so deployments can assert deterministic behaviour.

These logs help verify provenance when running manual smoke tests or CI pipelines.
