import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.api.main import app
from backend.database import Base, get_db

SAMPLE_CSV = b"""machine,planned_production_time_hours,downtime_hours,units_produced,good_units,ideal_cycle_time_seconds,failure_count,energy_kwh
Line 1,720,45,50000,48500,40,12,18000
Line 2,720,20,62000,61200,38,4,21000
"""


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


def test_kpi_computation_matches_expected_values(client, workspace_id):
    resp = client.post(
        f"/workspaces/{workspace_id}/kpi",
        files={"file": ("kpi.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2

    line1 = next(r for r in results if r["machine"] == "Line 1")
    assert round(line1["availability"], 3) == 0.938
    assert round(line1["oee"], 3) == 0.748
    assert round(line1["mtbf_hours"], 2) == 56.25
    assert round(line1["mttr_hours"], 2) == 3.75
    assert round(line1["scrap_rate"], 3) == 0.03


def test_kpi_rejects_unknown_workspace(client):
    resp = client.post(
        "/workspaces/999/kpi",
        files={"file": ("kpi.csv", io.BytesIO(SAMPLE_CSV), "text/csv")},
    )
    assert resp.status_code == 404


def test_kpi_rejects_missing_columns(client, workspace_id):
    bad_csv = b"machine,foo\nLine 1,1\n"
    resp = client.post(
        f"/workspaces/{workspace_id}/kpi",
        files={"file": ("kpi.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    assert resp.status_code == 400
