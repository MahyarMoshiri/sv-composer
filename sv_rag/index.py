"""Lightweight retrieval index for schema/metaphor/frame lookups."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sv_sdk.models import FrameBank, FrameItem, GoldLabel, MetaphorBank, MetaphorItem, SchemaBank, SchemaItem

from .embeddings import Embedder


ALLOWED_KINDS = {"schema", "metaphor", "frame", "exemplar"}


@dataclass
class Document:
    """Single indexed document."""

    doc_id: str
    kind: str
    lang: str
    text: str
    tags: List[str] = field(default_factory=list)
    weight: float = 1.0
    vector: np.ndarray = field(repr=False, default_factory=lambda: np.zeros(1, dtype=np.float32))
    payload: Optional[Dict[str, Any]] = None


@dataclass
class Hit:
    """Search result entry."""

    doc_id: str
    kind: str
    score: float
    tags: List[str]


class RAGIndex:
    """In-memory cosine similarity index built around a deterministic embedder."""

    def __init__(
        self,
        documents: Sequence[Document],
        embedder: Embedder,
        *,
        schema_bank: SchemaBank,
        metaphor_bank: MetaphorBank,
        frame_bank: FrameBank,
        gold: Sequence[GoldLabel] | None = None,
    ) -> None:
        self._documents: List[Document] = list(documents)
        self.embedder = embedder
        self.schema_bank = schema_bank
        self.metaphor_bank = metaphor_bank
        self.frame_bank = frame_bank
        self.gold = list(gold or [])

        self._schema_lookup: Dict[str, SchemaItem] = {s.id: s for s in schema_bank.schemas}
        self._metaphor_lookup: Dict[str, MetaphorItem] = {m.id: m for m in metaphor_bank.metaphors}
        self._frame_lookup: Dict[str, FrameItem] = {f.id: f for f in frame_bank.frames}

        self._kind_to_indices: Dict[str, List[int]] = {}
        self._doc_lookup: Dict[Tuple[str, str], Document] = {}

        vectors: List[np.ndarray] = []
        for index, document in enumerate(self._documents):
            vector = np.asarray(document.vector, dtype=np.float32)
            norm = float(np.linalg.norm(vector))
            if norm > 0:
                vector = vector / norm
            document.vector = vector
            self._kind_to_indices.setdefault(document.kind, []).append(index)
            self._doc_lookup[(document.kind, document.doc_id)] = document
            vectors.append(vector)

        self._matrix = np.stack(vectors, axis=0) if vectors else np.zeros((0, 0), dtype=np.float32)

    def get_document(self, doc_id: str, kind: str) -> Optional[Document]:
        return self._doc_lookup.get((kind, doc_id))

    def stats(self) -> Dict[str, int]:
        return {kind: len(indices) for kind, indices in self._kind_to_indices.items()}

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._documents)

    def frame(self, frame_id: str) -> Optional[FrameItem]:
        return self._frame_lookup.get(frame_id)

    def schema(self, schema_id: str) -> Optional[SchemaItem]:
        return self._schema_lookup.get(schema_id)

    def metaphor(self, metaphor_id: str) -> Optional[MetaphorItem]:
        return self._metaphor_lookup.get(metaphor_id)

    def search(
        self,
        query: str,
        *,
        k: int = 8,
        filter_kinds: Optional[Sequence[str]] = None,
        lang: Optional[str] = None,
    ) -> List[Hit]:
        """Search the index using cosine similarity."""

        if k <= 0 or not self._documents:
            return []

        encoded = self.embedder.encode([query])
        if not encoded:
            return []
        vector = np.asarray(encoded[0], dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        if norm == 0:
            return []
        vector /= norm

        if filter_kinds:
            allow = [kind for kind in filter_kinds if kind in ALLOWED_KINDS]
            indices: List[int] = []
            for kind in allow:
                indices.extend(self._kind_to_indices.get(kind, []))
            indices = sorted(set(indices))
        else:
            indices = list(range(len(self._documents)))

        hits: List[Hit] = []
        for idx in indices:
            document = self._documents[idx]
            if lang is not None and document.lang != lang:
                continue
            score = float(np.dot(vector, document.vector))
            if document.weight != 1.0:
                score *= document.weight
            if score <= 0:
                continue
            hits.append(
                Hit(
                    doc_id=document.doc_id,
                    kind=document.kind,
                    score=score,
                    tags=list(document.tags),
                )
            )

        hits.sort(key=lambda h: (-h.score, h.kind, h.doc_id))
        return hits[:k]


def _lexicon_tokens(items: Iterable) -> List[str]:
    tokens: List[str] = []
    for item in items:
        lemma = getattr(item, "lemma", None)
        if lemma:
            tokens.append(str(lemma))
    return tokens


def _schema_text(schema: SchemaItem) -> str:
    parts: List[str] = [schema.definition]
    parts.extend(schema.examples.text)
    parts.extend(_lexicon_tokens(schema.lexicon.en))
    parts.extend(_lexicon_tokens(schema.lexicon.fa))
    return "\n".join(part for part in parts if part)


def _metaphor_text(metaphor: MetaphorItem) -> str:
    parts: List[str] = [metaphor.definition]
    parts.extend(metaphor.examples.text)
    parts.extend(_lexicon_tokens(metaphor.lexicon.en))
    parts.extend(_lexicon_tokens(metaphor.lexicon.fa))
    axis = getattr(metaphor, "axis", None)
    if axis:
        parts.append(str(axis))
    return "\n".join(part for part in parts if part)


def _frame_text(frame: FrameItem) -> str:
    parts: List[str] = [frame.definition]
    if frame.role_notes:
        parts.extend(frame.role_notes.values())
    if frame.motif_hints:
        parts.extend(frame.motif_hints)
    if frame.allowed_schemas:
        parts.extend(frame.allowed_schemas)
    if frame.allowed_metaphors:
        parts.extend(frame.allowed_metaphors)
    return "\n".join(part for part in parts if part)


def _exemplar_payload(label: GoldLabel) -> Dict[str, Any]:
    schemas = [ann.id for ann in label.labels.schemas]
    metaphors = [ann.id for ann in label.labels.metaphors]
    poles = {ann.id: ann.pole for ann in label.labels.metaphors if ann.pole}
    frame_id = label.labels.frame.id if label.labels.frame else None
    return {
        "schemas": schemas,
        "metaphors": metaphors,
        "poles": poles,
        "frame": frame_id,
        "text": label.text,
    }


def _exemplar_text(label: GoldLabel, payload: Mapping[str, Any]) -> str:
    parts = [label.text]
    if payload.get("schemas"):
        parts.append("Schemas: " + ", ".join(payload["schemas"]))
    if payload.get("metaphors"):
        parts.append("Metaphors: " + ", ".join(payload["metaphors"]))
    if payload.get("frame"):
        parts.append(f"Frame: {payload['frame']}")
    return "\n".join(parts)


def build_index(
    banks: Mapping[str, Any],
    gold: Sequence[GoldLabel],
    embedder: Embedder,
) -> RAGIndex:
    """Construct a retrieval index over schemas, metaphors, frames, and gold exemplars."""

    schema_bank = banks.get("schemas")
    metaphor_bank = banks.get("metaphors")
    frame_bank = banks.get("frames")
    if not isinstance(schema_bank, SchemaBank):
        raise TypeError("banks['schemas'] must be a SchemaBank")
    if not isinstance(metaphor_bank, MetaphorBank):
        raise TypeError("banks['metaphors'] must be a MetaphorBank")
    if not isinstance(frame_bank, FrameBank):
        raise TypeError("banks['frames'] must be a FrameBank")

    documents: List[Document] = []
    texts: List[str] = []
    metadata: List[Dict[str, Any]] = []

    def queue(
        kind: str,
        doc_id: str,
        lang: str,
        text: str,
        *,
        tags: Iterable[str],
        weight: float = 1.0,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        if kind not in ALLOWED_KINDS:
            return
        texts.append(text)
        metadata.append(
            {
                "kind": kind,
                "doc_id": doc_id,
                "lang": lang,
                "text": text,
                "tags": list(dict.fromkeys(tags)),
                "weight": float(weight),
                "payload": payload,
            }
        )

    for schema in sorted(schema_bank.schemas, key=lambda item: item.id):
        queue(
            "schema",
            schema.id,
            "en",
            _schema_text(schema),
            tags=[schema.id],
            weight=1.0,
        )

    for metaphor in sorted(metaphor_bank.metaphors, key=lambda item: item.id):
        queue(
            "metaphor",
            metaphor.id,
            "en",
            _metaphor_text(metaphor),
            tags=[metaphor.id] + list(dict.fromkeys(metaphor.bipolar)),
            weight=1.0,
        )

    for frame in sorted(frame_bank.frames, key=lambda item: item.id):
        queue(
            "frame",
            frame.id,
            "en",
            _frame_text(frame),
            tags=[frame.id] + list(dict.fromkeys(frame.allowed_schemas + frame.allowed_metaphors)),
            weight=1.0,
        )

    for label in sorted(gold, key=lambda item: item.id):
        payload = _exemplar_payload(label)
        tags = list(payload.get("schemas", [])) + list(payload.get("metaphors", []))
        frame_id = payload.get("frame")
        if frame_id:
            tags.append(frame_id)
        queue(
            "exemplar",
            label.id,
            label.lang,
            _exemplar_text(label, payload),
            tags=tags,
            weight=1.0,
            payload=payload,
        )

    encoded = embedder.encode(texts)
    vectors = [np.asarray(vec, dtype=np.float32) for vec in encoded]

    for meta, vector in zip(metadata, vectors):
        documents.append(
            Document(
                doc_id=meta["doc_id"],
                kind=meta["kind"],
                lang=meta["lang"],
                text=meta["text"],
                tags=meta["tags"],
                weight=meta["weight"],
                vector=vector,
                payload=meta.get("payload"),
            )
        )

    return RAGIndex(
        documents,
        embedder,
        schema_bank=schema_bank,
        metaphor_bank=metaphor_bank,
        frame_bank=frame_bank,
        gold=gold,
    )
