# P11 — LLM Harness & Integration

The LLM harness wraps third-party models behind a consistent interface so upstream
controllers only depend on `generate(prompt, max_new_tokens)`.

## Overview
- **Protocol:** `sv_llm.harness.LLM` defines the minimal `generate()` contract.
- **Core factory:** `get_llm(name=None)` loads the configured harness, with
  `load_llm()` kept as a backwards-compatible alias.
- **Defaults:** When online, `openai` is the primary harness; otherwise
  `echo` (deterministic stub).
- **Fallback:** `_FallbackOnErrorLLM` switches to the echo harness after the
  first runtime failure from the primary provider.

## Environment Controls
Set these in `.env` or the process environment:

| Variable | Default | Description |
| --- | --- | --- |
| `SV_LLM_DEFAULT` | `openai` | Chooses which harness `get_llm()` returns. `echo` forces offline mode. |
| `SV_OFFLINE` | unset | When `1`, forces the echo harness regardless of other settings. |
| `SV_LLM_IMPL` | unset | Dotted module path for a custom provider. Harness must expose a factory (see below). |
| `SV_LLM_FACTORY` | `create_llm` | Factory symbol to import from the custom provider module. |
| `OPENAI_API_KEY` | unset | Required for the built-in OpenAI harness. Optional `OPENAI_BASE_URL` overrides the API host. |
| `SV_OPENAI_MODEL` | `gpt-5` | Model name passed to the OpenAI client. |
| `SV_OPENAI_TEMPERATURE` | `0.7` | Float temperature for completions. |
| `SV_OPENAI_TIMEOUT` | `20` | Request timeout (seconds). |

`default_llm_name()` inspects the environment and reports the effective harness
without actually instantiating it—useful for status endpoints.

## Built-in Providers
- **EchoLLM:** Deterministic stub used for tests and offline smoke runs. It
  echoes the first non-empty prompt line within the token budget.
- **OpenAI:** Wraps the v1 `openai` SDK (`sv_llm.providers.openai`). It requires
  a valid API key and raises if the SDK or key is missing.

`get_llm()` returns `_FallbackOnErrorLLM(openai, EchoLLM())` when `SV_LLM_DEFAULT`
resolves to `openai`. Any exception from the primary harness is logged and the
fallback stub is used for the remainder of the process.

## Custom Providers
To use a custom model, set `SV_LLM_IMPL=/path/to/module` and optionally
`SV_LLM_FACTORY`. The module must expose the factory:

```python
# my_llm_provider.py
from sv_llm.harness import LLM

class MyLLM(LLM):
    def generate(self, prompt: str, max_new_tokens: int = 200) -> str:
        return "..."

def create_llm(*, name: str) -> MyLLM:
    return MyLLM()
```

Run with:

```bash
SV_LLM_IMPL=my_llm_provider SV_LLM_FACTORY=create_llm \
SV_LLM_DEFAULT=myllm uvicorn sv_api.main:app --reload
```

Any import or instantiation error falls back to `EchoLLM` and logs a warning.

## Integration Points
- **Generation API:** `/generate` loads the harness once via `get_llm()` and
  runs `run_beat()` per beat, using `critic.md`/`revise.md` for quality control.
- **Compose-only flows:** Offline composing (`/compose`, SDK) stays deterministic
  because the harness is only invoked in P8 (`sv_compose.generate`).
- **Status logging:** API startup logs `default_llm_name()` and whether an OpenAI
  key is present (`sv_api.main._log_llm_default`).

## Testing & Offline Mode
- No network calls during unit tests; `SV_OFFLINE=1` ensures `EchoLLM` and keeps
  deterministic snapshots.
- Missing SDK or API key automatically downgrades to echo, so CI does not need
  secret management.

## Tips
1. Use `SV_OFFLINE=1` for deterministic smoke runs.
2. If you rely on a custom provider, ship the module alongside deployment and
   ensure the factory returns an object with `generate()`.
3. Monitor logs for `Primary LLM failed; switching to EchoLLM` to catch runtime
   provider issues.
