import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.ai.client import get_anthropic_client
from backend.api.main import app
from backend.database import Base, get_db


class _FakeToolUseBlock:
    def __init__(self, input_data):
        self.type = "tool_use"
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def create(self, **kwargs):
        return _FakeResponse(
            [
                _FakeToolUseBlock(
                    {
                        "executive_summary": "Acme faces a critical inflection point...",
                        "current_situation": "Acme operates with frequent downtime...",
                        "key_findings": ["Weekly unplanned downtime", "No supply chain visibility"],
                        "financial_impact": "Downtime costs an estimated...",
                        "next_steps": ["Deploy IoT sensors", "Pilot predictive maintenance"],
                    }
                )
            ]
        )


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

    app.dependency_overrides[get_db] = override_get_db
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


def test_narrative_requires_at_least_one_finding(client, workspace_id):
    resp = client.post(f"/workspaces/{workspace_id}/executive-report/narrative", json={})
    assert resp.status_code == 400


def test_narrative_generates_from_partial_findings(client, workspace_id):
    # Only SWOT provided — Roadmap/Maturity/Technology/KPI intentionally
    # omitted, proving the endpoint works with a partial set, not just
    # when every module has been run first.
    payload = {
        "swot": {
            "strengths": [{"item": "Experienced workforce", "explanation": "..."}],
            "weaknesses": [{"item": "High machine downtime", "explanation": "..."}],
            "opportunities": [],
            "threats": [],
        }
    }
    resp = client.post(f"/workspaces/{workspace_id}/executive-report/narrative", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["executive_summary"]
    assert len(body["key_findings"]) == 2
    assert len(body["next_steps"]) == 2


def test_narrative_rejects_unknown_workspace(client):
    resp = client.post(
        "/workspaces/999/executive-report/narrative",
        json={"swot": {"strengths": [], "weaknesses": [], "opportunities": [], "threats": []}},
    )
    assert resp.status_code == 404
