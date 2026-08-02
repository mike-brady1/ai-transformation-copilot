import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from backend.models.document import Document
from backend.rag.chunking import chunk_text

_embedding_fn = DefaultEmbeddingFunction()


def get_chroma_client():
    """FastAPI dependency, same pattern as get_db: tests override this
    to swap in an in-memory client so nothing touches disk or leaks
    between test runs."""
    return chromadb.PersistentClient(path="./chroma_db")


def get_collection(client, workspace_id: int):
    # One collection per workspace: a search in Acme's engagement can
    # never surface a Nova Robotics chunk, because it's a different
    # collection entirely, not just a filtered query.
    return client.get_or_create_collection(
        name=f"workspace_{workspace_id}_docs",
        embedding_function=_embedding_fn,
    )


def reindex_workspace_documents(client, db, workspace_id: int) -> None:
    """Self-heals a real failure mode: Chroma's storage can live on an
    ephemeral disk (wiped on redeploy) while Postgres — where Document
    rows are recorded — doesn't. If that happens, a document exists on
    paper with no searchable content. Re-embeds every Document row's
    stored `content` for this workspace, but only when the collection is
    actually empty — a single collection.count() check, so this is
    nearly free on the (overwhelmingly common) case where nothing is
    wrong.
    """
    collection = get_collection(client, workspace_id)
    if collection.count() > 0:
        return

    documents = db.query(Document).filter(Document.workspace_id == workspace_id).all()
    for document in documents:
        if not document.content:
            continue  # predates the content column — nothing to recover from
        chunks = chunk_text(document.content)
        if not chunks:
            continue
        collection.add(
            documents=chunks,
            ids=[f"doc{document.id}_chunk{i}" for i in range(len(chunks))],
            metadatas=[
                {"source": document.filename, "document_id": document.id, "chunk_index": i}
                for i in range(len(chunks))
            ],
        )


def get_full_workspace_context(client, db, workspace_id: int) -> str | None:
    """Every chunk from every document in a workspace, ordered and
    labeled by source — not a similarity search. Used by any module that
    needs the whole picture (SWOT, Roadmap, Digital Maturity), as opposed
    to Chat's top-k retrieval for one specific question. Returns None if
    no documents have been uploaded yet."""
    reindex_workspace_documents(client, db, workspace_id)
    collection = get_collection(client, workspace_id)
    result = collection.get()
    if not result["documents"]:
        return None

    ordered = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda pair: (pair[0].get("document_id", 0), pair[0].get("chunk_index", 0)),
    )
    return "\n\n---\n\n".join(f"[Source: {meta.get('source')}]\n{doc}" for meta, doc in ordered)
