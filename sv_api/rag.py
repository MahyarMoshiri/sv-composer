"""RAG index bootstrap utilities for API handlers."""
from __future__ import annotations

from functools import lru_cache
from typing import Tuple

from sv_rag.embeddings import HashEmbedder
from sv_rag.index import RAGIndex, build_index
from sv_sdk.gold_loader import load_gold_jsonl
from sv_sdk.loader import load_frame_bank, load_metaphor_bank, load_schema_bank


@lru_cache(maxsize=1)
def _rag_bundle() -> Tuple[RAGIndex, HashEmbedder]:
    banks = {
        "schemas": load_schema_bank(),
        "metaphors": load_metaphor_bank(),
        "frames": load_frame_bank(),
    }
    gold = load_gold_jsonl()
    embedder = HashEmbedder()
    index = build_index(banks, gold, embedder)
    return index, embedder


def get_rag_index() -> RAGIndex:
    return _rag_bundle()[0]


def get_embedder_name() -> str:
    # Currently only the hash embedder is supported.
    return "hash"
