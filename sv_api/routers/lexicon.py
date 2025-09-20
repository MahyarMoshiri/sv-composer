"""Lexicon matching endpoints."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Query

from sv_control.lexicon import match_lemmas

router = APIRouter()


@router.get("/bible/schemas/lexicon")
def get_lexicon_matches(text: str = Query(..., min_length=1), lang: str = "en") -> Dict[str, object]:
    matches = match_lemmas(text=text, lang=lang)
    return {"lang": lang, "text": text, "matches": matches}
