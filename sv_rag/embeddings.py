"""Deterministic embedding utilities for offline retrieval."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Iterable, Iterator, List, Protocol
import unicodedata

import numpy as np


class Embedder(Protocol):
    """Protocol for simple text embedders used by the RAG index."""

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode input texts into a list of float vectors."""
        raise NotImplementedError


def _normalize_text(text: str) -> str:
    """Lower-case and normalize unicode text for hashing."""

    normalized = unicodedata.normalize("NFKC", text).lower()
    # Collapse consecutive whitespace to a single space for stability.
    return " ".join(normalized.split())


def _char_trigrams(text: str) -> Iterator[str]:
    """Yield overlapping character trigrams with simple padding."""

    padded = f"  {text}  "
    for index in range(len(padded) - 2):
        yield padded[index : index + 3]


@dataclass
class HashEmbedder:
    """Deterministic bag-of-character-trigram embedder.

    The embedder hashes each trigram into a fixed number of buckets and returns
    an L2-normalised vector so cosine similarity can be applied downstream.
    """

    dim: int = 4096

    def __post_init__(self) -> None:
        if self.dim <= 0:
            raise ValueError("dim must be a positive integer")

    def _bucket(self, trigram: str) -> int:
        digest = hashlib.blake2b(trigram.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % self.dim

    def encode(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            if not isinstance(text, str):  # defensive cast
                text = "" if text is None else str(text)
            normalized = _normalize_text(text)
            accumulator = np.zeros(self.dim, dtype=np.float32)

            for trigram in _char_trigrams(normalized):
                bucket = self._bucket(trigram)
                accumulator[bucket] += 1.0

            norm = float(np.linalg.norm(accumulator))
            if norm > 0:
                accumulator /= norm
            vectors.append(accumulator.tolist())
        return vectors
