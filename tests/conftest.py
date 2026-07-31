import chromadb
from chromadb.config import Settings

# Both functions below must use identical Settings — chromadb keys its
# shared in-memory instance by (identifier, settings) and raises if two
# clients claim the same "ephemeral" identifier with different settings.
_SETTINGS = Settings(allow_reset=True)


def reset_shared_chroma_store():
    """Call exactly once per test, before making any requests.

    chromadb.EphemeralClient() instances created in the same process share
    their underlying in-memory store (cached internally by settings, not
    truly per-instance) — without resetting, a collection named e.g.
    "workspace_1_docs" created in one test file leaks into any other test
    file that also happens to use workspace_id=1 (which is every test
    file here, since each uses its own fresh SQLite DB where ids restart
    at 1). Confirmed this empirically before trusting it as the fix.

    Only call this from test setup, never from inside the FastAPI
    dependency override itself — that runs once per request, and
    resetting there would wipe data added by an earlier request in the
    same test (e.g. an upload followed by a search), since every
    EphemeralClient() instance shares that one store.
    """
    client = chromadb.EphemeralClient(settings=_SETTINGS)
    client.reset()


def fresh_chroma_client():
    """FastAPI dependency override — safe to call on every request."""
    return chromadb.EphemeralClient(settings=_SETTINGS)
