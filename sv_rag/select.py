"""Utilities for selecting active schemas and metaphors for composition."""
from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence

from sv_sdk.models import FrameItem, MetaphorItem, SchemaItem

from .index import Document, RAGIndex


def _unique(sequence: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    order: List[str] = []
    for item in sequence:
        if item and item not in seen:
            seen.add(item)
            order.append(item)
    return order


def _select_with_constraints(
    hits: Sequence[str],
    *,
    required: Sequence[str],
    allowed: Sequence[str],
    disallowed: Sequence[str],
    limit: int,
) -> List[str]:
    selected = _unique(required)
    limit = max(limit, len(selected))
    allowed_set = set(filter(None, allowed))
    disallowed_set = set(filter(None, disallowed))

    def permitted(identifier: str) -> bool:
        if identifier in disallowed_set:
            return False
        if allowed_set and identifier not in allowed_set:
            return False
        return True

    for identifier in hits:
        if len(selected) >= limit:
            break
        if identifier in selected:
            continue
        if permitted(identifier):
            selected.append(identifier)

    if len(selected) < limit:
        for identifier in allowed:
            if len(selected) >= limit:
                break
            if identifier in selected or identifier in disallowed_set:
                continue
            selected.append(identifier)

    return selected[:limit]


def _gather_lexicon(
    schemas: Iterable[str],
    metaphors: Iterable[str],
    *,
    index: RAGIndex,
) -> Dict[str, Dict[str, List[str]]]:
    lexicon: Dict[str, Dict[str, List[str]]] = {"schemas": {}, "metaphors": {}}
    for schema_id in schemas:
        schema: SchemaItem | None = index.schema(schema_id)
        if not schema:
            continue
        lexicon["schemas"][schema_id] = {
            "en": [entry.lemma for entry in schema.lexicon.en],
            "fa": [entry.lemma for entry in schema.lexicon.fa],
        }

    for metaphor_id in metaphors:
        metaphor: MetaphorItem | None = index.metaphor(metaphor_id)
        if not metaphor:
            continue
        lexicon["metaphors"][metaphor_id] = {
            "en": [entry.lemma for entry in metaphor.lexicon.en],
            "fa": [entry.lemma for entry in metaphor.lexicon.fa],
        }

    return lexicon


def _score_exemplar(
    document: Document,
    *,
    frame_id: str,
    schemas: Sequence[str],
    metaphors: Sequence[str],
) -> int:
    payload = document.payload or {}
    score = 0
    if payload.get("frame") == frame_id:
        score += 2
    schema_overlap = set(payload.get("schemas", [])) & set(schemas)
    metaphor_overlap = set(payload.get("metaphors", [])) & set(metaphors)
    if schema_overlap:
        score += 1
    if metaphor_overlap:
        score += 1
    return score


def select_active(
    frame_id: str,
    query: str,
    *,
    top_schemas: int = 3,
    top_metaphors: int = 2,
    index: RAGIndex,
) -> Dict[str, object]:
    """Select active schemas, metaphors, and exemplars for the supplied frame."""

    frame: FrameItem | None = index.frame(frame_id)
    if frame is None:
        raise ValueError(f"Unknown frame_id '{frame_id}'")

    schema_hits = index.search(query, k=max(top_schemas * 4, 8), filter_kinds=["schema"])
    schema_ids = [hit.doc_id for hit in schema_hits]

    metaphor_hits = index.search(query, k=max(top_metaphors * 4, 8), filter_kinds=["metaphor"])
    metaphor_ids = [hit.doc_id for hit in metaphor_hits]

    selected_schemas = _select_with_constraints(
        schema_ids,
        required=frame.required_schemas,
        allowed=frame.allowed_schemas,
        disallowed=frame.disallowed_schemas,
        limit=top_schemas,
    )

    selected_metaphors = _select_with_constraints(
        metaphor_ids,
        required=[],
        allowed=frame.allowed_metaphors,
        disallowed=frame.disallowed_metaphors,
        limit=top_metaphors,
    )

    exemplar_hits = index.search(query, k=12, filter_kinds=["exemplar"])
    exemplar_candidates: List[tuple[int, Document]] = []
    for hit in exemplar_hits:
        document = index.get_document(hit.doc_id, hit.kind)
        if not document:
            continue
        score = _score_exemplar(
            document,
            frame_id=frame_id,
            schemas=selected_schemas,
            metaphors=selected_metaphors,
        )
        exemplar_candidates.append((score, document))

    exemplar_candidates.sort(key=lambda item: (-item[0], item[1].doc_id))
    selected_exemplars: List[Document] = []
    for score, document in exemplar_candidates:
        if len(selected_exemplars) >= 4:
            break
        if score == 0 and selected_exemplars:
            continue
        selected_exemplars.append(document)

    poles: Dict[str, str] = {}
    for document in selected_exemplars:
        payload = document.payload or {}
        pole_map: Mapping[str, str | None] = payload.get("poles", {})  # type: ignore[assignment]
        for metaphor_id, pole in pole_map.items():
            if not pole:
                continue
            metaphor = index.metaphor(metaphor_id)
            if not metaphor or metaphor.type != "bipolar":
                continue
            if metaphor_id in selected_metaphors and metaphor_id not in poles:
                poles[metaphor_id] = pole

    lexicon = _gather_lexicon(selected_schemas, selected_metaphors, index=index)

    exemplars_payload = [
        {
            "lang": document.lang,
            "text": (document.payload or {}).get("text", document.text),
        }
        for document in selected_exemplars
    ]

    return {
        "schemas": selected_schemas,
        "metaphors": selected_metaphors,
        "poles": poles,
        "exemplars": exemplars_payload,
        "lexicon": lexicon,
    }
