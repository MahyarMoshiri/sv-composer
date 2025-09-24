"""Trace objects emitted during composition planning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ComposeTraceBeat:
    beat: str
    expectation_target: float
    selected_schemas: List[str]
    selected_metaphors: List[str]
    poles: Dict[str, str]
    tokens: Dict[str, List[str]]
    prompts: Dict[str, str]
    outputs: Dict[str, Any] = field(default_factory=dict)
    plan: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "beat": self.beat,
            "expectation_target": self.expectation_target,
            "selected_schemas": list(self.selected_schemas),
            "selected_metaphors": list(self.selected_metaphors),
            "poles": dict(self.poles),
            "tokens": {
                "must": list(self.tokens.get("must", [])),
                "ban": list(self.tokens.get("ban", [])),
            },
            "prompts": dict(self.prompts),
            "outputs": dict(self.outputs),
            "plan": dict(self.plan),
        }


@dataclass
class ComposeTrace:
    frame_id: str
    beats: List[ComposeTraceBeat]
    curve_before: List[float]
    curve_after: List[float]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "beats": [beat.as_dict() for beat in self.beats],
            "curve_before": list(self.curve_before),
            "curve_after": list(self.curve_after),
        }
