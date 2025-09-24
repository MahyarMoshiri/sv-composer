"""Evaluator API endpoints."""
from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Mapping, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sv_api.utils import err, ok
from sv_compose.controller import get_thresholds_config
from sv_eval.evaluator import evaluate as run_evaluator
from sv_sdk.loader import load_frame_bank, load_metaphor_bank, load_schema_bank

router = APIRouter()


class EvaluateRequest(BaseModel):
    piece: str
    trace: Dict[str, Any] = Field(default_factory=dict)


class EvaluateBatchItem(BaseModel):
    id: str
    piece: str
    trace: Dict[str, Any] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def _banks_bundle() -> Mapping[str, Any]:
    return {
        "schemas": load_schema_bank(),
        "metaphors": load_metaphor_bank(),
        "frames": load_frame_bank(),
    }


def _evaluate_payload(piece: str, trace: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    thresholds = get_thresholds_config()
    result = run_evaluator(piece, trace or {}, thresholds, _banks_bundle())
    return result


@router.post("/evaluate")
def evaluate(payload: EvaluateRequest) -> Dict[str, Any]:
    try:
        result = _evaluate_payload(payload.piece, payload.trace)
    except Exception as exc:  # noqa: BLE001 - surfaced to API caller
        return err([str(exc)])
    return ok(result)


@router.post("/evaluate/batch")
def evaluate_batch(items: List[EvaluateBatchItem]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    errors: List[str] = []
    for item in items:
        try:
            payload = _evaluate_payload(item.piece, item.trace)
            results.append({"id": item.id, "result": payload})
        except Exception as exc:  # noqa: BLE001 - surfaced to API caller
            errors.append(f"{item.id}: {exc}")
    data = {"results": results}
    if errors:
        return {"ok": False, "data": data, "warnings": [], "errors": errors}
    return ok(data)


__all__ = ["evaluate", "evaluate_batch"]
