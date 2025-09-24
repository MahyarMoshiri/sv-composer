from __future__ import annotations

from sv_rag.embeddings import HashEmbedder
from sv_rag.index import build_index
from sv_sdk.gold_loader import load_gold_jsonl
from sv_sdk.loader import load_frame_bank, load_metaphor_bank, load_schema_bank


def test_build_and_search_rag_index() -> None:
    banks = {
        "schemas": load_schema_bank(),
        "metaphors": load_metaphor_bank(),
        "frames": load_frame_bank(),
    }
    gold = load_gold_jsonl()
    index = build_index(banks, gold, HashEmbedder())
    hits = index.search("bridge room dusk", k=5, filter_kinds=["schema", "frame"])
    assert len(hits) > 0
