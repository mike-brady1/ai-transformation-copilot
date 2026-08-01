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
    def create(self, **kwargs):
        # Dispatch on which tool is being requested — this route makes
        # two sequential Claude calls (SWOT, then Roadmap), so the fake
        # needs to return the right canned response for each step.
        tool_name = kwargs["tools"][0]["name"]

        if tool_name == "record_swot":
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        {
                            "strengths": [{"item": "Experienced workforce", "explanation": "..."}],
                            "weaknesses": [{"item": "High machine downtime", "explanation": "..."}],
                            "opportunities": [{"item": "Predictive maintenance", "explanation": "..."}],
                            "threats": [{"item": "Production downtime costs", "explanation": "..."}],
                        }
                    )
                ]
            )

        if tool_name == "record_roadmap":
            return _FakeResponse(
                [
                    _FakeToolUseBlock(
                        {
                            "quick_wins": [
                                {
                                    "initiative": "IoT vibration sensors",
                                    "business_value": "Early warning on failures",
                                    "estimated_cost": "Low",
                                    "complexity": "Low",
                                    "implementation_effort": "Install on top 3 machines",
                                    # Deliberately using the wrong key,
                                    # mirroring the real Claude quirk found
                                    # in Colab (capitalizing ROI) — proves
                                    # the Optional-field defense works.
                                    "expected_ROI": "High",
                                    "dependencies": "None",
                                }
                            ],
                            "medium_term": [],
                            "long_term": [],
                        }
                    )
                ]
            )

        raise ValueError(f"Unexpected tool: {tool_name}")


class _FakeAnthropicClient:
    def __init__(self):
        self.messages = _FakeMessages()


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

    reset_shared_chroma_store()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_chroma_client] = fresh_chroma_client
    app.dependency_overrides[get_anthropic_client] = lambda: _FakeAnthropicClient()
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


def test_roadmap_requires_documents_first(client, workspace_id):
    resp = client.post(f"/workspaces/{workspace_id}/roadmap")
    assert resp.status_code == 400


def test_roadmap_generates_three_horizons(client, workspace_id):
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

    resp = client.post(f"/workspaces/{workspace_id}/roadmap")
    assert resp.status_code == 200
    roadmap = resp.json()
    assert len(roadmap["quick_wins"]) == 1
    assert roadmap["medium_term"] == []
    assert roadmap["long_term"] == []


def test_roadmap_survives_mismatched_field_name_from_claude(client, workspace_id):
    """Regression test for the real bug found in Colab: Claude sometimes
    emits 'expected_ROI' instead of the schema's 'expected_return'. This
    should not 500 — the field should just come back empty."""
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

    resp = client.post(f"/workspaces/{workspace_id}/roadmap")
    assert resp.status_code == 200
    initiative = resp.json()["quick_wins"][0]
    assert initiative["initiative"] == "IoT vibration sensors"
    assert initiative["expected_return"] is None


def test_roadmap_rejects_unknown_workspace(client):
    resp = client.post("/workspaces/999/roadmap")
    assert resp.status_code == 404
