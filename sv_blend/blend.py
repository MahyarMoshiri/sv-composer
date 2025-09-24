"""Deterministic blending engine with audit output."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List, Sequence, Tuple

from sv_sdk.models import BlendRules, FrameOverride


ROLE_LIKE = {
    "agent",
    "boundary",
    "goal",
    "path",
    "traveler",
    "crosser",
    "seer",
    "holder",
    "target",
}


@dataclass
class SceneActive:
    schemas: List[str]
    metaphors: List[str]
    poles: Dict[str, str]
    gates: List[str] = field(default_factory=list)
    frame_id: str | None = None
    explosion_fired: bool = False


@dataclass(frozen=True)
class Space:
    label: str
    schemas: Tuple[str, ...] = field(default_factory=tuple)
    metaphors: Tuple[str, ...] = field(default_factory=tuple)
    poles: Dict[str, str] = field(default_factory=dict)
    gates: Tuple[str, ...] = field(default_factory=tuple)
    frame_id: str | None = None


@dataclass(frozen=True)
class Mapping:
    left: str
    right: str
    relation: str
    rationale: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "left": self.left,
            "right": self.right,
            "relation": self.relation,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class BlendStep:
    operator: str
    relation: str
    cost: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "operator": self.operator,
            "relation": self.relation,
            "cost": round(self.cost, 4),
        }


def _dedupe_preserve(items: Sequence[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def _split_pole_values(value: str) -> Tuple[str, ...]:
    tokens = [token.strip() for token in re.split(r"[\s,|]+", value) if token.strip()]
    return tuple(dict.fromkeys(tokens))


def _axis_tokens(poles: Dict[str, str]) -> Tuple[str, ...]:
    tokens: List[str] = []
    for axis, raw_value in poles.items():
        tokens.append(axis)
        parts = _split_pole_values(raw_value)
        for part in parts:
            tokens.append(part)
            tokens.append(f"{axis}:{part}")
    return tuple(dict.fromkeys(tokens))


def build_spaces(active: SceneActive) -> Tuple[Space, Space]:
    a = Space(
        label="input_a",
        schemas=_dedupe_preserve(active.schemas),
        gates=_dedupe_preserve(active.gates),
        frame_id=active.frame_id,
    )
    b = Space(
        label="input_b",
        metaphors=_dedupe_preserve(active.metaphors),
        poles=dict(active.poles),
    )
    return a, b


def _ensure_override(frame_id: str | None, rules: BlendRules) -> FrameOverride:
    if frame_id is None:
        return FrameOverride(frame_id=None)
    override = rules.frame_overrides.get(frame_id)
    if override is None:
        return FrameOverride(frame_id=frame_id)
    if override.frame_id is None:
        override = override.model_copy(update={"frame_id": frame_id})
    return override


def _relation_for(left: str, right: str, priority: Sequence[str]) -> str:
    if left in ROLE_LIKE or right in ROLE_LIKE:
        if "role" in priority:
            return "role"
    if left == right and "identity" in priority:
        return "identity"
    if ":" in right and "analogy" in priority:
        return "analogy"
    return priority[0] if priority else "identity"


def propose_mappings(space_a: Space, space_b: Space, rules: BlendRules) -> List[Mapping]:
    align = rules.counterpart_mapping
    allow_roles = set(align.role_alignment.allow)
    disallow_roles = set(align.role_alignment.disallow)
    non_projectable = set(align.non_projectable_features)
    priority = list(align.priority)

    features_a = list(space_a.schemas)
    if space_a.frame_id:
        features_a.append(space_a.frame_id)
    features_a.extend(space_a.gates)

    features_b = list(space_b.metaphors)
    features_b.extend(_axis_tokens(space_b.poles))
    # allow identity alignments when both inputs share the same feature label
    features_b.extend(features_a)

    seen: set[str] = set()
    mappings: List[Mapping] = []
    max_candidates = max(len(space_a.schemas), rules.constraints.max_blend_depth)
    if max_candidates <= 0:
        max_candidates = rules.constraints.max_blend_depth or 1

    for left in features_a:
        if left in non_projectable:
            continue
        for right in features_b:
            if right in non_projectable:
                continue
            pair = f"{left}↔{right}"
            inverse = f"{right}↔{left}"
            if pair in disallow_roles or inverse in disallow_roles:
                continue
            if pair not in allow_roles and inverse not in allow_roles and left != right:
                continue
            key = pair if pair in allow_roles else inverse
            if key in seen:
                continue
            relation = _relation_for(left, right, priority)
            rationale = "role_alignment" if key in allow_roles else "identity_alignment"
            mappings.append(Mapping(left=left, right=right, relation=relation, rationale=rationale))
            seen.add(key)
            if len(mappings) >= max_candidates:
                return mappings
    return mappings


def apply_operators(
    mappings: Sequence[Mapping],
    rules: BlendRules,
    frame_override: FrameOverride,
) -> Tuple[List[BlendStep], float]:
    allowed_ops = [
        op
        for op in rules.operators
        if op.id not in frame_override.disallowed_operators
        and (
            not frame_override.operator_whitelist
            or op.id in frame_override.operator_whitelist
        )
    ]

    if not allowed_ops:
        return [], 0.0

    prefer_relations = set(frame_override.prefer_relations or rules.compression_preferences.prefer)
    max_ops = frame_override.max_ops_per_blend or rules.constraints.max_ops_per_blend
    cost_adjust = frame_override.operator_cost_adjust or {}

    steps: List[BlendStep] = []
    usage: Dict[str, int] = {}
    total_cost = 0.0

    for mapping in mappings:
        if len(steps) >= max_ops:
            break
        candidates: List[Tuple[Tuple[int, int, float, str], BlendStep]] = []
        for operator in allowed_ops:
            if operator.allowed_relations and mapping.relation not in operator.allowed_relations:
                continue
            if mapping.relation in operator.disallowed_relations:
                continue
            base_cost = rules.scoring.operator_costs.get(operator.id, operator.cost)
            adjusted_cost = max(0.0, base_cost + cost_adjust.get(operator.id, 0.0))
            ranking = (
                0 if mapping.relation in prefer_relations else 1,
                0 if operator.safe else 1,
                usage.get(operator.id, 0),
                adjusted_cost,
                operator.id,
            )
            step = BlendStep(operator=operator.id, relation=mapping.relation, cost=adjusted_cost)
            candidates.append((ranking, step))

        if not candidates:
            continue
        candidates.sort(key=lambda item: item[0])
        chosen = candidates[0][1]
        steps.append(chosen)
        usage[chosen.operator] = usage.get(chosen.operator, 0) + 1
        total_cost += chosen.cost

    return steps, total_cost


def _frame_compatibility_score(active: SceneActive, rules: BlendRules) -> float:
    if not active.frame_id:
        return 1.0
    banned = {
        tuple(sorted(pair))
        for pair in rules.constraints.banned_frame_pairs
        if len(pair) == 2
    }
    frame_pair = tuple(sorted((active.frame_id, active.frame_id)))
    return 0.0 if frame_pair in banned else 1.0


def _schema_alignment_score(active: SceneActive, mappings: Sequence[Mapping]) -> float:
    if not active.schemas:
        return 1.0
    covered = {mapping.left for mapping in mappings if mapping.left in active.schemas}
    return min(1.0, len(covered) / len(set(active.schemas)))


def _metaphor_alignment_score(active: SceneActive, rules: BlendRules) -> float:
    metaphors = set(active.metaphors)
    for pair in rules.constraints.banned_metaphor_pairs:
        if len(pair) == 2 and set(pair).issubset(metaphors):
            return 0.0
    return 1.0 if metaphors else 0.5


def _minimality_score(steps: Sequence[BlendStep], max_ops: int) -> float:
    if not steps:
        return 1.0
    return 1.0 if len(steps) <= max_ops else max(0.0, 1.0 - (len(steps) - max_ops) * 0.25)


def _novelty_cap_score(mappings: Sequence[Mapping]) -> float:
    if not mappings:
        return 0.5
    return min(1.0, 0.6 + 0.1 * len(mappings))


def _polar_conflict_penalty(
    active: SceneActive,
    rules: BlendRules,
) -> Tuple[float, List[str]]:
    penalties: List[str] = []
    total = 0.0
    for axis, policy in rules.constraints.polar_conflicts.items():
        if axis not in active.metaphors and axis not in active.poles:
            continue
        value = active.poles.get(axis)
        if not value:
            continue
        tokens = _split_pole_values(value)
        if len(tokens) <= 1:
            continue
        if policy.allow_if_explosion_fired and active.explosion_fired:
            continue
        weight = rules.scoring.penalty.get("polar_conflict", 0.0)
        if weight:
            total += weight
            penalties.append(f"polar_conflict:{axis}")
    return total, penalties


def blend(active: SceneActive, rules: BlendRules) -> Dict[str, object]:
    space_a, space_b = build_spaces(active)
    frame_override = _ensure_override(active.frame_id, rules)
    mappings = propose_mappings(space_a, space_b, rules)
    steps, total_operator_cost = apply_operators(mappings, rules, frame_override)

    max_ops = frame_override.max_ops_per_blend or rules.constraints.max_ops_per_blend

    reward_metrics = {
        "frame_compat": _frame_compatibility_score(active, rules),
        "schema_alignment": _schema_alignment_score(active, mappings),
        "metaphor_alignment": _metaphor_alignment_score(active, rules),
        "minimality": _minimality_score(steps, max_ops),
        "novelty_cap": _novelty_cap_score(mappings),
    }

    rewards: Dict[str, Dict[str, float]] = {}
    reward_total = 0.0
    for name, metric in reward_metrics.items():
        weight = rules.scoring.reward.get(name, 0.0)
        contribution = weight * metric
        rewards[name] = {
            "metric": round(metric, 4),
            "weight": round(weight, 4),
            "contribution": round(contribution, 4),
        }
        reward_total += contribution

    score_pre_penalty = reward_total - total_operator_cost

    penalties: List[Dict[str, object]] = []
    penalty_total = 0.0

    if len(mappings) > rules.constraints.max_blend_depth:
        weight = rules.scoring.penalty.get("depth_overflow", 0.0)
        if weight:
            penalty_total += weight
            penalties.append({"reason": "depth_overflow", "weight": round(weight, 4)})

    if not mappings:
        weight = rules.scoring.penalty.get("unknown_mapping", 0.0)
        if weight:
            penalty_total += weight
            penalties.append({"reason": "unknown_mapping", "weight": round(weight, 4)})
    elif active.frame_id and not steps:
        weight = rules.scoring.penalty.get("frame_incompatibility", 0.0)
        if weight:
            penalty_total += weight
            penalties.append({"reason": "frame_incompatibility", "weight": round(weight, 4)})

    schema_set = set(active.schemas)
    for pair in rules.constraints.banned_schema_pairs:
        if len(pair) == 2 and set(pair).issubset(schema_set):
            weight = rules.scoring.penalty.get("banned_pair", 0.0)
            if weight:
                penalty_total += weight
                penalties.append({"reason": "banned_schema_pair", "pair": pair, "weight": round(weight, 4)})
                break

    metaphor_set = set(active.metaphors)
    for pair in rules.constraints.banned_metaphor_pairs:
        if len(pair) == 2 and set(pair).issubset(metaphor_set):
            weight = rules.scoring.penalty.get("banned_pair", 0.0)
            if weight:
                penalty_total += weight
                penalties.append({"reason": "banned_metaphor_pair", "pair": pair, "weight": round(weight, 4)})
                break

    if active.frame_id:
        for pair in rules.constraints.banned_frame_pairs:
            if len(pair) == 2 and active.frame_id in pair:
                other = pair[0] if pair[1] == active.frame_id else pair[1]
                if other == active.frame_id:
                    continue
                weight = rules.scoring.penalty.get("banned_pair", 0.0)
                if weight:
                    penalty_total += weight
                    penalties.append({"reason": "banned_frame_pair", "pair": pair, "weight": round(weight, 4)})
                    break

    polar_total, polar_tags = _polar_conflict_penalty(active, rules)
    if polar_total:
        penalty_total += polar_total
        for tag in polar_tags:
            penalties.append({"reason": tag, "weight": round(rules.scoring.penalty.get("polar_conflict", 0.0), 4)})

    score_final = score_pre_penalty - penalty_total
    accepted = score_final >= rules.scoring.accept_threshold

    audit = {
        "spaces": {
            space_a.label: {
                "schemas": list(space_a.schemas),
                "gates": list(space_a.gates),
                "frame_id": space_a.frame_id,
            },
            space_b.label: {
                "metaphors": list(space_b.metaphors),
                "poles": space_b.poles,
            },
        },
        "mappings": [mapping.to_dict() for mapping in mappings],
        "operators": [step.to_dict() for step in steps],
        "costs": {"operator_total": round(total_operator_cost, 4)},
        "rewards": rewards,
        "penalties": penalties,
        "thresholds": {
            "accept": round(rules.scoring.accept_threshold, 4),
            "max_depth": rules.constraints.max_blend_depth,
            "max_ops": max_ops,
        },
        "flags": {"explosion_fired": active.explosion_fired},
    }

    decisions = {
        "operators": [step.operator for step in steps],
        "mappings": len(mappings),
    }

    return {
        "accepted": accepted,
        "score_pre_penalty": round(score_pre_penalty, 4),
        "score_final": round(score_final, 4),
        "decisions": decisions,
        "audit": audit,
    }
