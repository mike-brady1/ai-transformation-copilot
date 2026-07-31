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
