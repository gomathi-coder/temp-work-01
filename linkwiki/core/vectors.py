"""ChromaDB vector store — embed entry summaries, semantic search, clustering."""

from __future__ import annotations
import numpy as np
from linkwiki.core.config import CHROMA_DIR, EMBED_MODEL

_collection = None
_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb  # type: ignore
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_or_create_collection(
            "entry_summaries",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _doc(title: str | None, summary: str | None) -> str:
    return f"{title or ''}\n\n{summary or ''}".strip()[:2_000]


# ── Write ──────────────────────────────────────────────────────────────────

def embed_entry(
    entry_id: str,
    title: str | None,
    summary: str | None,
    url_type: str,
    tags: list[str],
) -> None:
    doc = _doc(title, summary)
    if not doc:
        return
    vec = _get_model().encode([doc])[0].tolist()
    _get_collection().upsert(
        ids=[entry_id],
        embeddings=[vec],
        documents=[doc],
        metadatas=[{"url_type": url_type, "tags": ",".join(tags)}],
    )


def delete_entry(entry_id: str) -> None:
    try:
        _get_collection().delete(ids=[entry_id])
    except Exception:
        pass


# ── Read ───────────────────────────────────────────────────────────────────

def search(query: str, n: int = 10, url_type: str | None = None) -> list[dict]:
    """Return top-N entries by semantic similarity to query."""
    col = _get_collection()
    if col.count() == 0:
        return []
    vec = _get_model().encode([query])[0].tolist()
    kwargs: dict = dict(query_embeddings=[vec], n_results=min(n, col.count()))
    if url_type:
        kwargs["where"] = {"url_type": url_type}
    results = col.query(**kwargs)
    out = []
    for entry_id, distance in zip(results["ids"][0], results["distances"][0]):
        out.append({"id": entry_id, "similarity": round(1 - distance, 4)})
    return out


def similar_to(entry_id: str, n: int = 20) -> list[dict]:
    """Return the top-N entries most similar to a given entry."""
    col = _get_collection()
    if col.count() < 2:
        return []
    existing = col.get(ids=[entry_id], include=["embeddings"])
    if not existing["embeddings"]:
        return []
    vec = existing["embeddings"][0]
    results = col.query(
        query_embeddings=[vec],
        n_results=min(n + 1, col.count()),
    )
    out = []
    for eid, distance in zip(results["ids"][0], results["distances"][0]):
        if eid != entry_id:
            out.append({"id": eid, "similarity": round(1 - distance, 4)})
    return out


def get_all_embeddings() -> tuple[list[str], np.ndarray] | tuple[None, None]:
    """Return (entry_ids, embedding_matrix) for all stored entries."""
    col = _get_collection()
    if col.count() == 0:
        return None, None
    data = col.get(include=["embeddings"])
    ids = data["ids"]
    matrix = np.array(data["embeddings"], dtype=np.float32)
    return ids, matrix


def count() -> int:
    return _get_collection().count()
