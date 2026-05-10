"""RAG indexing: chunk → ModelScope embedding → ChromaDB."""

from __future__ import annotations

import logging

from backend.core.config import settings
from backend.core.model_clients import modelscope_embed
from backend.core.storage import ensure_project_dirs
from backend.models.material import Chunk

logger = logging.getLogger(__name__)

_http_chroma_client = None
_persistent_chroma_clients: dict[str, object] = {}


def _get_chroma(project_id: str | None = None):
    global _http_chroma_client
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError as exc:
        raise RuntimeError(
            "ChromaDB is required for RAG indexing. Install backend requirements first."
        ) from exc

    if settings.chroma_host:
        if _http_chroma_client is None:
            _http_chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return _http_chroma_client

    storage_project_id = project_id or "_shared"
    if storage_project_id not in _persistent_chroma_clients:
        persist_path = str(ensure_project_dirs(storage_project_id)["chroma"])
        _persistent_chroma_clients[storage_project_id] = chromadb.PersistentClient(
            path=persist_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _persistent_chroma_clients[storage_project_id]


async def build_rag_index(project_id: str, chunks: list[Chunk]) -> dict:
    """Embed all chunks and store in ChromaDB. Returns index stats."""
    if not chunks:
        return {"indexed": 0, "error": "No chunks provided"}

    client = _get_chroma(project_id)
    collection_name = f"{project_id}_chunks"

    # Remove existing collection if rebuilding
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    # Batch embed
    batch_size = 32
    ids: list[str] = []
    metadatas: list[dict] = []
    documents: list[str] = []
    all_vectors: list[list[float]] = []

    skipped: list[dict] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c.text for c in batch]

        try:
            vectors = await modelscope_embed(texts)
        except Exception as exc:
            logger.warning(
                "Embedding batch failed; retrying chunks individually",
                extra={"project_id": project_id, "offset": i, "error": str(exc)[:300]},
            )
            vectors = []
            kept_batch: list[Chunk] = []
            for chunk in batch:
                try:
                    vector = (await modelscope_embed([chunk.text]))[0]
                except Exception as item_exc:
                    skipped.append({
                        "chunk_id": chunk.id,
                        "textbook": chunk.textbook,
                        "chapter": chunk.chapter,
                        "error": str(item_exc)[:300],
                    })
                    logger.warning(
                        "Skipping unembeddable chunk",
                        extra={
                            "project_id": project_id,
                            "chunk_id": chunk.id,
                            "textbook": chunk.textbook,
                            "chapter": chunk.chapter,
                            "error": str(item_exc)[:300],
                        },
                    )
                    continue
                kept_batch.append(chunk)
                vectors.append(vector)
            batch = kept_batch

        for chunk, vector in zip(batch, vectors):
            ids.append(chunk.id)
            metadatas.append(chunk.citation_metadata())
            documents.append(chunk.text)
            all_vectors.append(vector)

    if all_vectors:
        collection.add(
            ids=ids,
            embeddings=all_vectors,
            documents=documents,
            metadatas=metadatas,
        )

    logger.info(
        "RAG index built",
        extra={
            "project_id": project_id,
            "chunk_count": len(chunks),
            "indexed_count": len(ids),
            "skipped_count": len(skipped),
            "embedding_dim": len(all_vectors[0]) if all_vectors else 0,
        },
    )

    return {
        "indexed": len(ids),
        "skipped": len(skipped),
        "collection": collection_name,
        "skippedSamples": skipped[:10],
    }


async def search_chunks(
    project_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Search indexed chunks by semantic similarity. Returns list of {chunk, score, metadata}."""
    client = _get_chroma(project_id)
    collection_name = f"{project_id}_chunks"

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []

    query_vector = await modelscope_embed([query])

    results = collection.query(
        query_embeddings=query_vector,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output: list[dict] = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            output.append({
                "chunk_id": results["ids"][0][i],
                "text": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
            })

    return output
