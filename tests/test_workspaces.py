import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.main import app
from backend.database import Base, get_db


@pytest.fixture()
def client(tmp_path):
    # A fresh, throwaway SQLite file per test — so tests never touch the
    # real workspaces.db and never leak state into each other.
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

    # Swap the real DB dependency for the test one, only for this test.
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_create_and_list_workspace(client):
    resp = client.post(
        "/workspaces",
        json={
            "client_name": "Acme Manufacturing",
            "industry": "Automotive",
            "employees": 1500,
            "countries": ["France", "Germany"],
            "current_erp": "SAP S/4HANA",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == 1

    resp = client.get("/workspaces")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["client_name"] == "Acme Manufacturing"
