import requests

from config import API_BASE_URL


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


def send_chat_message(workspace_id: int, messages: list[dict]) -> dict:
    resp = requests.post(
        f"{API_BASE_URL}/workspaces/{workspace_id}/chat", json={"messages": messages}
    )
    resp.raise_for_status()
    return resp.json()
