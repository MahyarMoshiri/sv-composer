import os
from typing import Literal

Provider = Literal["openai", "local"]

def generate_text(prompt: str, provider: Provider = "local") -> str:
    # Deterministic stub
    return f"[hook] {prompt}\n[build] footsteps echo\n[turn] the bridge hums\n[reveal] the river answers"
