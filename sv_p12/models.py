"""Data models for the P12 single-prompt film planning workflow."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    """Pydantic base model that forbids unknown fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BeatName(str, Enum):
    hook = "hook"
    setup = "setup"
    development = "development"
    turn = "turn"
    reveal = "reveal"
    settle = "settle"


class AllocationMode(str, Enum):
    EqualSplit = "EqualSplit"
    CurveWeighted = "CurveWeighted"


class SinglePromptRequest(StrictBaseModel):
    """Incoming request payload for the single-prompt film planner."""

    prompt: str
    frame_id: Optional[str] = None
    beats: List[BeatName] = Field(default_factory=list)
    total_duration_sec: float = 60.0
    scene_length_sec: float = 5.0
    aspect_ratio: str = "16:9"
    style_pack: Optional[str] = None
    allocation_mode: AllocationMode = AllocationMode.CurveWeighted
    llm_enrich: bool = False
    seed: Optional[int] = None
    temperature: Optional[float] = None


class ScenePrompt(StrictBaseModel):
    """Production-ready prompt instructions for a single scene."""

    scene_id: str
    beat: BeatName
    start_sec: float
    duration_sec: float
    prompt: str
    negative_prompt: str
    camera: str
    lighting: str
    color: str
    framing: str
    movement: str
    motion: str
    audio: str
    transition_in: str
    transition_out: str
    safety_tags: List[str]
    seed: Optional[int] = None
    aspect_ratio: str = "16:9"
    notes: Optional[str] = None


class SequencePlan(StrictBaseModel):
    """Collection of scenes grouped by beat."""

    beat: BeatName
    intent: str
    scenes: List[ScenePrompt]


class FilmPlan(StrictBaseModel):
    """Top-level film planning response."""

    frame_id: str
    total_duration_sec: float
    scene_length_sec: float
    aspect_ratio: str
    style_pack: Optional[str] = None
    sequences: List[SequencePlan]
    warnings: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any]


__all__ = [
    "AllocationMode",
    "BeatName",
    "FilmPlan",
    "ScenePrompt",
    "SequencePlan",
    "SinglePromptRequest",
]
