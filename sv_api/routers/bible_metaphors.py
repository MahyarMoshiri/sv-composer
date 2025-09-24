"""Routes exposing metaphor bible content."""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from sv_api.utils import err, ok
from sv_sdk.loader import load_metaphor_bank
from sv_sdk.models import MetaphorBank, MetaphorItem
from sv_sdk.validators import validate_metaphor_bank

router = APIRouter()


def _metaphor_summary(bank: MetaphorBank) -> Dict[str, int | str]:
    metaphors = bank.metaphors
    return {
        "version": bank.version,
        "count": len(metaphors),
        "en_lex": sum(len(item.lexicon.en) for item in metaphors),
        "fa_lex": sum(len(item.lexicon.fa) for item in metaphors),
    }


def _serialize(metaphors: List[MetaphorItem]) -> List[Dict[str, object]]:
    return [metaphor.model_dump(mode="python", by_alias=True) for metaphor in metaphors]


@router.get("/bible/metaphors")
def get_metaphors(
    id: Optional[str] = Query(default=None),
    validate: bool = Query(default=False),
):
    bank = load_metaphor_bank()

    warnings: List[str] = []
    if validate:
        try:
            warnings = validate_metaphor_bank(bank)
        except Exception as exc:  # noqa: BLE001 - surface validation failures
            return JSONResponse(status_code=422, content=err([str(exc)]))

    items: List[MetaphorItem] = list(bank.metaphors)
    if id is not None:
        items = [metaphor for metaphor in items if metaphor.id == id]

    payload: Dict[str, object] = {
        "summary": _metaphor_summary(bank),
        "metaphors": _serialize(items),
    }
    if warnings:
        payload["warnings"] = warnings

    return ok(payload)
