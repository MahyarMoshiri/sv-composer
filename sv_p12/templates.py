"""Unified template loader for P12.

Prefers shared templates under `prompts/templates/` and falls back to
module-local copies under `sv_p12/templates/` if not present.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts" / "templates"
LOCAL_DIR = Path(__file__).resolve().parent / "templates"


def _first_existing(*candidates: Path) -> Path:
    for p in candidates:
        if p.exists():
            return p
    # Return the first candidate regardless to surface a clear error on read
    return candidates[0]


VIDEO_TPL = _first_existing(PROMPTS_DIR / "video_prompt_v1.txt", LOCAL_DIR / "video_prompt_v1.txt")
SFX_TPL = _first_existing(PROMPTS_DIR / "sfx_prompt_v1.txt", LOCAL_DIR / "sfx_prompt_v1.txt")
STYLE_SYS_TPL = _first_existing(PROMPTS_DIR / "style_enrich_v1.system.txt", LOCAL_DIR / "style_enrich_v1.system.txt")
STYLE_USR_TPL = _first_existing(PROMPTS_DIR / "style_enrich_v1.user.txt", LOCAL_DIR / "style_enrich_v1.user.txt")
STYLE_RESP_DOC = _first_existing(PROMPTS_DIR / "style_enrich_v1.response.md", LOCAL_DIR / "style_enrich_v1.response.md")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def style_enrich_templates() -> Tuple[str, str]:
    return read(STYLE_SYS_TPL), read(STYLE_USR_TPL)


__all__ = [
    "VIDEO_TPL",
    "SFX_TPL",
    "STYLE_SYS_TPL",
    "STYLE_USR_TPL",
    "STYLE_RESP_DOC",
    "read",
    "style_enrich_templates",
]

