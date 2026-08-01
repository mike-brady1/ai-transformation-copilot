import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

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


def get_full_workspace_context(client, workspace_id: int) -> str | None:
    """Every chunk from every document in a workspace, ordered and
    labeled by source — not a similarity search. Used by any module that
    needs the whole picture (SWOT, Roadmap, Digital Maturity), as opposed
    to Chat's top-k retrieval for one specific question. Returns None if
    no documents have been uploaded yet."""
    collection = get_collection(client, workspace_id)
    result = collection.get()
    if not result["documents"]:
        return None

    ordered = sorted(
        zip(result["metadatas"], result["documents"]),
        key=lambda pair: (pair[0].get("document_id", 0), pair[0].get("chunk_index", 0)),
    )
    return "\n\n---\n\n".join(f"[Source: {meta.get('source')}]\n{doc}" for meta, doc in ordered)
