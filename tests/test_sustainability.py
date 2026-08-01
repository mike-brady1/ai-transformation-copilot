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

SAMPLE_CSV = b"""machine,planned_production_time_hours,downtime_hours,units_produced,good_units,ideal_cycle_time_seconds,failure_count,energy_kwh
Line 1,720,45,50000,48500,40,12,18000
Line 2,720,20,62000,61200,38,4,21000
Line 3,720,90,41000,38000,45,18,16500
"""
# energy sum = 55500, units sum = 153000


class _FakeToolUseBlock:
    def __init__(self, input_data):
        self.type = "tool_use"
        self.input = input_data


class _FakeResponse:
    def __init__(self, content):
        self.content = content


class _FakeMessages:
    def __init__(self, factor=0.475):
        self._factor = factor

    def create(self, **kwargs):
        payload = {
            "emissions_factor_assumption": "Assumed a typical mixed industrial grid.",
            "waste_assessment": "Insufficient evidence in provided documents",
            "transportation_assessment": "Limited visibility into post-factory logistics.",
            "opportunities": [
                {
                    "initiative": "Solar PV installation",
                    "description": "Offset grid electricity with rooftop solar.",
                    "estimated_impact": "Medium",
                }
            ],
        }
        if self._factor is not None:
            payload["emissions_factor_kg_co2_per_kwh"] = self._factor
        return _FakeResponse([_FakeToolUseBlock(payload)])


class _FakeAnthropicClient:
    def __init__(self, factor=0.475):
        self.messages = _FakeMessages(factor)


def _make_client(tmp_path, factor=0.475):
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
    app.dependency_overrides[get_anthropic_client] = lambda: _FakeAnthropicClient(factor)
    return TestClient(app)


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


def test_sustainability_computes_exact_values(client, workspace_id):
    resp = client.post(
        f"/workspaces/{workspace_id}/sustainability",
        files={"file": ("kpi.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_energy_kwh"] == 55500
    assert body["total_units_produced"] == 153000
    # 55500 / 153000 = 0.362745... -> rounded to 0.3627
    assert body["energy_intensity_kwh_per_unit"] == 0.3627
    # 55500 * 0.475 = 26362.5, computed by our code, not Claude
    assert body["estimated_co2_emissions_kg"] == 26362.5
    assert body["emissions_factor_kg_co2_per_kwh"] == 0.475
    assert len(body["opportunities"]) == 1


def test_sustainability_falls_back_to_default_factor_when_missing(tmp_path):
    # The fake omits emissions_factor_kg_co2_per_kwh entirely — proves the
    # route's defensive fallback, not just the happy path.
    test_client = _make_client(tmp_path, factor=None)
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

    resp = test_client.post(
        f"/workspaces/{workspace_id}/sustainability",
        files={"file": ("kpi.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["emissions_factor_kg_co2_per_kwh"] == 0.475  # DEFAULT_EMISSIONS_FACTOR
    assert "defaulted" in body["emissions_factor_assumption"].lower()
    app.dependency_overrides.clear()


def test_sustainability_rejects_missing_columns(client, workspace_id):
    bad_csv = b"machine,foo\nLine 1,1\n"
    resp = client.post(
        f"/workspaces/{workspace_id}/sustainability",
        files={"file": ("kpi.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert resp.status_code == 400


def test_sustainability_rejects_unknown_workspace(client):
    resp = client.post(
        "/workspaces/999/sustainability",
        files={"file": ("kpi.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert resp.status_code == 404
