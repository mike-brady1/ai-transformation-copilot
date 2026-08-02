import requests

from config import API_BASE_URL


def error_detail(exc: requests.exceptions.RequestException) -> str:
    """Pulls FastAPI's {"detail": "..."} message out of a failed
    response when there is one, instead of showing a generic message
    that can't distinguish 'backend unreachable' from 'backend responded
    but rejected the request for a specific, useful reason'."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json().get("detail")
            if detail:
                return detail
        except ValueError:
            pass
    return str(exc)


def create_workspace(payload: dict) -> dict:
    resp = requests.post(f"{API_BASE_URL}/workspaces", json=payload)
    resp.raise_for_status()
    return resp.json()


def list_workspaces() -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}/workspaces")
    resp.raise_for_status()
    return resp.json()


def upload_document(workspace_id: int, filename: str, file_bytes: bytes) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/documents",
        files={"file": (filename, file_bytes)},
    )
    resp.raise_for_status()
    return resp.json()


def list_documents(workspace_id: int) -> list[dict]:
    resp = requests.get(f"{API_BASE_URL}/workspaces/{workspace_id}/documents")
    resp.raise_for_status()
    return resp.json()


def delete_document(workspace_id: int, document_id: int) -> None:
    resp = requests.delete(f"{API_BASE_URL}/workspaces/{workspace_id}/documents/{document_id}")
    resp.raise_for_status()


def analyze_document(workspace_id: int, document_id: int) -> list[dict]:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/documents/{document_id}/analyze"
    )
    resp.raise_for_status()
    return resp.json()


def upload_kpi_csv(workspace_id: int, filename: str, file_bytes: bytes) -> list[dict]:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/kpi",
        files={"file": (filename, file_bytes)},
    )
    resp.raise_for_status()
    return resp.json()


def generate_swot(workspace_id: int) -> dict:
    resp = requests.post(f"{API_BASE_URL}/workspaces/{workspace_id}/swot")
    resp.raise_for_status()
    return resp.json()


def generate_roadmap(workspace_id: int) -> dict:
    resp = requests.post(f"{API_BASE_URL}/workspaces/{workspace_id}/roadmap")
    resp.raise_for_status()
    return resp.json()


def generate_digital_maturity(workspace_id: int) -> dict:
    resp = requests.post(f"{API_BASE_URL}/workspaces/{workspace_id}/maturity")
    resp.raise_for_status()
    return resp.json()


def generate_technology_recommendations(workspace_id: int) -> dict:
    resp = requests.post(f"{API_BASE_URL}/workspaces/{workspace_id}/technology-recommendations")
    resp.raise_for_status()
    return resp.json()


def generate_sustainability_report(workspace_id: int, filename: str, file_bytes: bytes) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/sustainability",
        files={"file": (filename, file_bytes)},
    )
    resp.raise_for_status()
    return resp.json()


def generate_executive_report_narrative(workspace_id: int, payload: dict) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/executive-report/narrative", json=payload
    )
    resp.raise_for_status()
    return resp.json()


def send_chat_message(workspace_id: int, messages: list[dict]) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/chat", json={"messages": messages}
    )
    resp.raise_for_status()
    return resp.json()
