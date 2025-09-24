"""Lexicon matching endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from sv_api.utils import ok
from sv_control.lexicon import match_lemmas

router = APIRouter()


@router.get("/bible/schemas/lexicon")
def get_lexicon_matches(text: str = Query(""), lang: str = Query("en")) -> dict:
    matches = match_lemmas(text=text, lang=lang)
    payload = {"lang": lang, "text": text, "scores": matches}
    return ok(payload)
