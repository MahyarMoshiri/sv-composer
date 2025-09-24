"""Pydantic models for the Schema Bank."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class ParamSpec(BaseModel):
    """Specification for a schema parameter."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal["enum", "float", "int", "bool"] = Field(alias="type")
    values: Optional[List[Any]] = None
    min: Optional[float] = None
    max: Optional[float] = None
    default: Optional[Any] = None
    unit: Optional[str] = None


class Lexeme(BaseModel):
    """Lexical item with an associated weight."""

    lemma: str
    w: float


class Affect(BaseModel):
    """Affect signature for a schema."""

    model_config = ConfigDict(extra="allow")

    valence: float
    arousal: float
    tags: Optional[List[str]] = None


class Provenance(BaseModel):
    """Provenance metadata for a schema."""

    source: str
    curator: str
    license: str
    confidence: float


class Examples(BaseModel):
    """Textual and visual examples for a schema."""

    model_config = ConfigDict(extra="allow")

    text: List[str] = Field(default_factory=list)
    visual: List[str] = Field(default_factory=list)


class Lexicon(BaseModel):
    """Lexicon entries keyed by language."""

    model_config = ConfigDict(extra="allow")

    en: List[Lexeme] = Field(default_factory=list)
    fa: List[Lexeme] = Field(default_factory=list)


class MetaphorGating(BaseModel):
    """Expectation gating parameters for a metaphor."""

    beats_bias: str
    expectation_increment: float


class MetaphorItem(BaseModel):
    """Single metaphor entry in the metaphor bank."""

    model_config = ConfigDict(extra="allow")

    id: str
    type: Literal["primary", "bipolar"]
    definition: str
    source_schema: Optional[str] = None
    axis: Optional[str] = None
    bipolar: List[str] = Field(default_factory=list)
    affect: Affect
    pole_affect: Dict[str, Affect] = Field(default_factory=dict)
    lexicon: Lexicon
    coactivate_schemas: List[str] = Field(default_factory=list)
    preferred_frames: List[str] = Field(default_factory=list)
    banned_with: List[str] = Field(default_factory=list)
    gating: MetaphorGating
    examples: Examples = Field(default_factory=Examples)
    provenance: Provenance
    target: Optional[str] = None


class MetaphorBank(BaseModel):
    """Collection of metaphors with a version identifier."""

    version: str
    metaphors: List[MetaphorItem]


class FrameViewpointDefaults(BaseModel):
    """Default narrator viewpoint cues suggested by a frame."""

    person: Literal["1st", "2nd", "3rd"] = "3rd"
    tense: Literal["past", "present"] = "present"
    distance: Literal["close", "medium", "far"] = "medium"


class FrameAttentionHint(BaseModel):
    """Suggested attention weighting for a frame role or schema."""

    model_config = ConfigDict(populate_by_name=True)

    role: Optional[str] = None
    schema_id: Optional[str] = Field(default=None, alias="schema")
    w: float


class FrameItem(BaseModel):
    """Single frame entry in the frame bank."""

    model_config = ConfigDict(extra="allow")

    id: str
    definition: str
    core_roles: List[str] = Field(default_factory=list)
    optional_roles: List[str] = Field(default_factory=list)
    role_notes: Dict[str, str] = Field(default_factory=dict)
    allowed_schemas: List[str] = Field(default_factory=list)
    required_schemas: List[str] = Field(default_factory=list)
    disallowed_schemas: List[str] = Field(default_factory=list)
    allowed_metaphors: List[str] = Field(default_factory=list)
    disallowed_metaphors: List[str] = Field(default_factory=list)
    metaphor_bias: Dict[str, float] = Field(default_factory=dict)
    viewpoint_defaults: FrameViewpointDefaults = Field(
        default_factory=FrameViewpointDefaults
    )
    attention_defaults: List[FrameAttentionHint] = Field(default_factory=list)
    gates_allowed: List[str] = Field(default_factory=list)
    motif_hints: List[str] = Field(default_factory=list)
    beat_affinity: Dict[str, float] = Field(default_factory=dict)
    examples: Examples = Field(default_factory=Examples)
    provenance: Provenance


class FrameBank(BaseModel):
    """Collection of frames with a version identifier."""

    version: str
    frames: List[FrameItem]


class SchemaItem(BaseModel):
    """Single schema entry."""

    id: str
    title: str
    definition: str
    roles: List[str] = Field(default_factory=list)
    params: Dict[str, ParamSpec] = Field(default_factory=dict)
    affect: Affect
    lexicon: Lexicon
    coactivate: List[str] = Field(default_factory=list)
    examples: Examples = Field(default_factory=Examples)
    provenance: Provenance


class SchemaBank(BaseModel):
    """Collection of schemas with a version identifier."""

    version: str
    schemas: List[SchemaItem]


class VitalRelation(BaseModel):
    """Core relations that license mappings between spaces."""

    id: str
    definition: str


class OperatorSpec(BaseModel):
    """Blending operator with safety and cost metadata."""

    id: str
    safe: bool
    cost: float
    allowed_relations: List[str] = Field(default_factory=list)
    disallowed_relations: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class RoleAlignmentSpec(BaseModel):
    """Allow/disallow lists for structural role alignments."""

    allow: List[str] = Field(default_factory=list)
    disallow: List[str] = Field(default_factory=list)


class AttributeAlignmentSpec(BaseModel):
    """Allow list for attribute-based alignments."""

    allow: List[str] = Field(default_factory=list)


class CounterpartMapping(BaseModel):
    """Rules governing how input counterparts may align."""

    role_alignment: RoleAlignmentSpec
    attribute_alignment: AttributeAlignmentSpec
    non_projectable_features: List[str] = Field(default_factory=list)
    priority: List[str] = Field(default_factory=list)


class CompressionPrefs(BaseModel):
    """Preferred vital relations during compression."""

    allow: List[str] = Field(default_factory=list)
    prefer: List[str] = Field(default_factory=list)
    disallow: List[str] = Field(default_factory=list)


class PolarConflictRule(BaseModel):
    """Policy for handling bipolar metaphor conflicts."""

    simultaneous_false: bool
    allow_if_explosion_fired: bool


class BlendConstraints(BaseModel):
    """Global hard limits on blend construction."""

    max_blend_depth: int
    max_ops_per_blend: int
    max_active_axes: int
    banned_schema_pairs: List[List[str]] = Field(default_factory=list)
    banned_metaphor_pairs: List[List[str]] = Field(default_factory=list)
    banned_frame_pairs: List[List[str]] = Field(default_factory=list)
    polar_conflicts: Dict[str, PolarConflictRule] = Field(default_factory=dict)


class FrameOverride(BaseModel):
    """Per-frame overrides for blending constraints."""

    frame_id: Optional[str] = None
    disallowed_operators: List[str] = Field(default_factory=list)
    operator_whitelist: List[str] = Field(default_factory=list)
    prefer_relations: List[str] = Field(default_factory=list)
    max_ops_per_blend: Optional[int] = None
    operator_cost_adjust: Dict[str, float] = Field(default_factory=dict)


class Scoring(BaseModel):
    """Scoring weights and thresholds for blends."""

    operator_costs: Dict[str, float] = Field(default_factory=dict)
    penalty: Dict[str, float] = Field(default_factory=dict)
    reward: Dict[str, float] = Field(default_factory=dict)
    accept_threshold: float


class BlendRules(BaseModel):
    """Complete blending rulebook curated in the bible."""

    version: str
    vital_relations: List[VitalRelation] = Field(default_factory=list)
    operators: List[OperatorSpec] = Field(default_factory=list)
    counterpart_mapping: CounterpartMapping
    compression_preferences: CompressionPrefs
    constraints: BlendConstraints
    frame_overrides: Dict[str, FrameOverride] = Field(default_factory=dict)
    scoring: Scoring
    examples: Optional[Dict[str, Any]] = None
    provenance: Optional[Provenance] = None


# --- Gold corpus models ----------------------------------------------------

Span = Tuple[int, int]


class GoldSchemaAnnotation(BaseModel):
    """Schema annotation with character spans."""

    id: str
    spans: List[Span] = Field(default_factory=list)


class GoldMetaphorAnnotation(BaseModel):
    """Metaphor annotation with optional pole and spans."""

    id: str
    pole: Optional[str] = None
    spans: List[Span] = Field(default_factory=list)


class GoldFrameAnnotation(BaseModel):
    """Frame annotation referencing a curated frame id."""

    id: str


class GoldViewpointAnnotation(BaseModel):
    """Narrator viewpoint cues captured for an example."""

    model_config = ConfigDict(extra="allow")

    person: Literal["1st", "2nd", "3rd"]
    tense: Literal["past", "present"]
    distance: Literal["close", "medium", "far"]


class GoldAttentionAnnotation(BaseModel):
    """Attention weighting over a span."""

    span: Span
    w: float


class GoldExplosionAnnotation(BaseModel):
    """Explosion annotation referencing the beat order."""

    beat: int
    confidence: float


class GoldLabels(BaseModel):
    """Structured annotation bundle for a labelled example."""

    schemas: List[GoldSchemaAnnotation] = Field(default_factory=list)
    metaphors: List[GoldMetaphorAnnotation] = Field(default_factory=list)
    frame: Optional[GoldFrameAnnotation] = None
    viewpoint: Optional[GoldViewpointAnnotation] = None
    attention: List[GoldAttentionAnnotation] = Field(default_factory=list)
    explosion: Optional[GoldExplosionAnnotation] = None


class GoldLabelProvenance(BaseModel):
    """Editorial provenance for a gold example."""

    curator: str
    source: str
    license: str
    confidence: float
    notes: Optional[str] = None


class GoldLabel(BaseModel):
    """Single gold-labelled example."""

    model_config = ConfigDict(extra="allow")

    id: str
    lang: Literal["en", "fa"]
    text: str
    labels: GoldLabels
    provenance: GoldLabelProvenance


GoldSet = List[GoldLabel]


class BeatSpec(BaseModel):
    """Single beat entry from the beats configuration."""

    model_config = ConfigDict(extra="allow")

    name: str
    order: Optional[int] = None


class BeatsConfig(BaseModel):
    """Configuration describing beat ordering and related metadata."""

    model_config = ConfigDict(extra="allow")

    version: Optional[str] = None
    beats: List[BeatSpec] = Field(default_factory=list)

    def ordered_beats(self) -> List[str]:
        """Return beats sorted by explicit order (fallback to declaration order)."""

        if not self.beats:
            return []
        with_order = [beat for beat in self.beats if beat.order is not None]
        if len(with_order) == len(self.beats):
            return [beat.name for beat in sorted(with_order, key=lambda item: item.order or 0)]
        return [beat.name for beat in self.beats]
