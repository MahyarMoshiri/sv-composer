"""Routes exposing the frame bible."""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from sv_api.utils import err, ok
from sv_sdk.loader import load_frame_bank
from sv_sdk.models import FrameBank, FrameItem
from sv_sdk.validators import validate_frame_bank

router = APIRouter()


def _frame_summary(bank: FrameBank) -> Dict[str, int | str]:
    frames = bank.frames
    return {
        "version": bank.version,
        "frames_count": len(frames),
        "core_roles": sum(len(frame.core_roles) for frame in frames),
        "optional_roles": sum(len(frame.optional_roles) for frame in frames),
    }


def _serialize(items: List[FrameItem]) -> List[Dict[str, object]]:
    return [frame.model_dump(mode="python", by_alias=True) for frame in items]


@router.get("/bible/frames")
def get_frames(
    id: Optional[str] = Query(default=None),
    validate: bool = Query(default=False),
):
    bank = load_frame_bank()

    warnings: List[str] = []
    if validate:
        try:
            warnings = validate_frame_bank(bank)
        except Exception as exc:  # noqa: BLE001 - surface validation errors
            return JSONResponse(status_code=422, content=err([str(exc)]))

    frames: List[FrameItem] = list(bank.frames)
    if id is not None:
        frames = [frame for frame in frames if frame.id == id]

    payload: Dict[str, object] = {
        "summary": _frame_summary(bank),
        "frames": _serialize(frames),
    }
    if warnings:
        payload["warnings"] = warnings

    return ok(payload)

