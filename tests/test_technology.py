import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.api.main import app
from backend.database import Base, get_db
from backend.rag.vector_store import get_chroma_client
from tests.conftest import fresh_chroma_client, reset_shared_chroma_store


class _FakeToolUseBlock:
    def __init__(self, input_data):
        self.type = "tool_use"
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, weaknesses):
        self._weaknesses = weaknesses

    def create(self, **kwargs):
        tool_name = kwargs["tools"][0]["name"]

        if tool_name == "record_swot":
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        {
                            "strengths": [],
                            "weaknesses": self._weaknesses,
                            "opportunities": [],
                            "threats": [],
                        }
                    )
                ]
            )

        if tool_name == "record_technology_recommendations":
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        {
                            "recommendations": [
                                {
                                    "problem": "High machine downtime",
                                    "recommendation": "Predictive Maintenance",
                                    "technology": "IoT Sensors",
                                    "platform": "Azure IoT",
                                    "expected_return": "High",
                                }
                            ]
                        }
                    )
                ]
            )

        raise AssertionError(
            f"Unexpected tool call: {tool_name} — should not happen when weaknesses is empty"
        )


class _FakeAnthropicClient:
    def __init__(self, weaknesses=None):
        default = [{"item": "High machine downtime", "explanation": "..."}]
        self.messages = _FakeMessages(default if weaknesses is None else weaknesses)


def _make_client(tmp_path, weaknesses=None):
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

    reset_shared_chroma_store()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chroma_client] = fresh_chroma_client
    app.dependency_overrides[get_anthropic_client] = lambda: _FakeAnthropicClient(weaknesses)
    test_client = TestClient(app)
    return test_client


@pytest.fixture()
def client(tmp_path):
    test_client = _make_client(tmp_path)
    yield test_client
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


def _upload_a_document(client, workspace_id):
    client.post(
        f"/workspaces/{workspace_id}/documents",
        files={
            "file": (
                "notes.txt",
                io.BytesIO(b"Machine failures happen almost every week."),
                "text/plain",
            )
        },
    )


def test_technology_requires_documents_first(client, workspace_id):
    resp = client.post(f"/workspaces/{workspace_id}/technology-recommendations")
    assert resp.status_code == 400


def test_technology_maps_weaknesses_to_recommendations(client, workspace_id):
    _upload_a_document(client, workspace_id)

    resp = client.post(f"/workspaces/{workspace_id}/technology-recommendations")
    assert resp.status_code == 200
    recommendations = resp.json()["recommendations"]
    assert len(recommendations) == 1
    assert recommendations[0]["problem"] == "High machine downtime"
    assert recommendations[0]["platform"] == "Azure IoT"


def test_technology_skips_second_call_when_no_weaknesses(tmp_path):
    # The fake's technology-tool branch raises if ever called — this
    # test passing at all proves the short-circuit actually happened,
    # not just that the response looked right.
    test_client = _make_client(tmp_path, weaknesses=[])
    resp = test_client.post(
        "/workspaces",
        json={
            "client_name": "Acme Manufacturing",
            "industry": "Automotive",
            "employees": 1500,
            "countries": ["France"],
        },
    )
    workspace_id = resp.json()["id"]
    _upload_a_document(test_client, workspace_id)

    resp = test_client.post(f"/workspaces/{workspace_id}/technology-recommendations")
    assert resp.status_code == 200
    assert resp.json()["recommendations"] == []
    app.dependency_overrides.clear()


def test_technology_rejects_unknown_workspace(client):
    resp = client.post("/workspaces/999/technology-recommendations")
    assert resp.status_code == 404
