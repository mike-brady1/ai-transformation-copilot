import io
from pathlib import Path

from pypdf import PdfReader


def load_text(filename: str, raw_bytes: bytes) -> str:
    """Extract plain text from an uploaded file's raw bytes, based on its extension."""
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt":
        return raw_bytes.decode("utf-8")

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError(f"Unsupported file type: {suffix}")
