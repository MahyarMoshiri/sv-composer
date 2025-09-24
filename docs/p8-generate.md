# P8 – Generate (Compose → Critic → Revise Loop)

P8 orchestrates the end-to-end loop after prompts have been rendered by P7.
The controller reuses the compose trace, executes each beat through a pluggable
LLM harness, applies `critic.md`, optionally runs one pass of `revise.md`, and
collects a final piece via `compose_final.md`.

## Pipeline

1. **Compose prompts** – call `/compose` (P7) to obtain per-beat system/context/compose prompts and trace metadata.
2. **Beat generation** – concatenate the prompts and call the chosen `LLM.generate()` implementation for each beat.
3. **Critic pass** – render `critic.md` for the beat context. A deterministic gate enforces length and banned-token checks locally; you may swap in a model call in production.
4. **One-shot revise** – if the critic fails, render `revise.md` and request a single revision from the harness, then re-run the local critic.
5. **Final assembly** – join accepted beat lines, respecting `max_lines`/`max_chars` from `thresholds.yml`, after rendering `compose_final.md` for auditability.

## Harness Swap

`sv_llm.harness` defines the minimal `LLM` protocol and ships with `EchoLLM` for offline tests.
Set `SV_LLM_IMPL="module.path"` (and optionally `SV_LLM_FACTORY`) to supply a real provider at runtime.
The `/generate` API selects the harness via the request body’s `llm` field.

## Example Request

```bash
curl -X POST http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "frame_id": "journey",
    "query": "inside the room at dusk",
    "beats": ["hook", "setup", "development", "turn", "reveal", "settle"],
    "llm": "echo"
  }'
```

Response fields:
- `beats`: per-beat `candidate`, `final`, and optional `revision` strings.
- `final`: assembled micro-poem respecting configured limits.
- `trace`: original compose trace plus a `critique` summary keyed by beat.
