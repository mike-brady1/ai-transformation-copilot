import io

import chromadb
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.main import app
from backend.database import Base, get_db
from backend.rag.vector_store import get_chroma_client


@pytest.fixture()
def client(tmp_path):
    test_engine = create_engine(
        f"sqlite:///{tmp_path}/test.db", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(test_engine)

    def override_get_db():
        db = Session(test_engine)
        try:
            yield db
        finally:
            db.close()

    def override_get_chroma_client():
        # In-memory only, isolated per test — same idea as the throwaway
        # SQLite file above, just for the vector store instead of the DB.
        return chromadb.EphemeralClient()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chroma_client] = override_get_chroma_client
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def workspace_id(client):
    resp = client.post(
        "/workspaces",
        json={
            "client_name": "Acme Manufacturing",
            "industry": "Automotive",
            "employees": 1500,
            "countries": ["France"],
        },
    )
    return resp.json()["id"]


def test_upload_document(client, workspace_id):
    file_content = b"Machine failures happen almost every week on line 3."
    resp = client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["filename"] == "notes.txt"
    assert body["chunk_count"] == 1
    assert body["workspace_id"] == workspace_id


def test_upload_rejects_unknown_workspace(client):
    resp = client.post(
        "/workspaces/999/documents",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 404


def test_search_finds_semantically_related_chunk(client, workspace_id):
    file_content = b"Machine failures happen almost every week on line 3."
    client.post(
        f"/workspaces/{workspace_id}/documents",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )

    resp = client.get(
        f"/workspaces/{workspace_id}/documents/search",
        params={"q": "is our equipment reliable?"},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert "machine failures" in results[0]["text"].lower()
