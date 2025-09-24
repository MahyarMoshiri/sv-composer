"""Route exposing the curated blending rules."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from sv_api.utils import err, ok
from sv_sdk.loader import (
    load_blend_rules,
    load_frame_bank,
    load_metaphor_bank,
    load_schema_bank,
)
from sv_sdk.models import BlendRules
from sv_sdk.validators import validate_blend_rules

router = APIRouter()


def _summary(rules: BlendRules) -> Dict[str, object]:
    return {
        "version": rules.version,
        "vital_relations": len(rules.vital_relations),
        "operators": len(rules.operators),
        "priority_relations": len(rules.counterpart_mapping.priority),
    }


@router.get("/bible/blend_rules")
def get_blend_rules(validate: bool = Query(default=False)):
    rules = load_blend_rules()

    if validate:
        try:
            validate_blend_rules(
                rules,
                load_frame_bank(),
                load_schema_bank(),
                load_metaphor_bank(),
            )
        except Exception as exc:  # noqa: BLE001 - bubble validation details
            return JSONResponse(status_code=422, content=err([str(exc)]))

    payload = {
        "summary": _summary(rules),
        "rules": rules.model_dump(mode="python", by_alias=True),
    }
    return ok(payload)
