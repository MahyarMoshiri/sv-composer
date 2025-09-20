"""Pydantic models for the Schema Bank."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

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
