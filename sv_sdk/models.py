from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

class Schema(BaseModel):
    id: str
    params: Dict[str, object] = Field(default_factory=dict)

class Frame(BaseModel):
    id: str
    allowed_schemas: List[str] = Field(default_factory=list)
    allowed_metaphors: List[str] = Field(default_factory=list)

class Metaphor(BaseModel):
    id: str
    source: Optional[str] = None
    target: Optional[str] = None
    bipolar: Optional[List[str]] = None
    affect: Dict[str, float] = Field(default_factory=dict)

class Bible(BaseModel):
    schemas: List[Schema]
    frames: List[Frame]
    metaphors: List[Metaphor]
    version: str
