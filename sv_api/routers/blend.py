"""Blending execution API."""
from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sv_api.utils import ok
from sv_blend.blend import SceneActive, blend
from sv_sdk.loader import load_blend_rules

router = APIRouter()


class BlendActiveModel(BaseModel):
    schemas: List[str] = Field(default_factory=list)
    metaphors: List[str] = Field(default_factory=list)
    poles: Dict[str, str] = Field(default_factory=dict)
    gates: List[str] = Field(default_factory=list)
    frame_id: Optional[str] = None


class BlendRequestModel(BaseModel):
    frame_id: Optional[str] = None
    active: BlendActiveModel
    explosion_fired: bool = False


BlendActiveModel.model_rebuild()
BlendRequestModel.model_rebuild()


@router.post("/blend")
def post_blend(request: BlendRequestModel):
    rules = load_blend_rules()
    frame_id = request.frame_id or request.active.frame_id

    scene = SceneActive(
        schemas=list(request.active.schemas),
        metaphors=list(request.active.metaphors),
        poles=dict(request.active.poles),
        gates=list(request.active.gates),
        frame_id=frame_id,
        explosion_fired=request.explosion_fired,
    )

    result = blend(scene, rules)
    response = ok(result)
    if result["audit"].get("penalties"):
        response["warnings"].append("penalties_applied")
    return response
