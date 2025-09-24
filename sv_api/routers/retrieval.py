"""Retrieval endpoints for the composition RAG index."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sv_api.rag import get_rag_index
from sv_api.utils import ok

router = APIRouter()


class RetrievalSearchIn(BaseModel):
    query: str
    k: int = Field(default=8, ge=1, le=32)
    kinds: Optional[List[str]] = None
    lang: Optional[str] = None


@router.post("/retrieval/search")
def search(payload: RetrievalSearchIn):
    index = get_rag_index()
    hits = index.search(
        payload.query,
        k=payload.k,
        filter_kinds=payload.kinds,
        lang=payload.lang,
    )

    response_hits = [
        {
            "doc_id": hit.doc_id,
            "kind": hit.kind,
            "score": round(hit.score, 6),
            "tags": hit.tags,
        }
        for hit in hits
    ]

    return ok({"hits": response_hits, "warnings": []})
