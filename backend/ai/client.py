import os
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

# Local equivalent of Colab's Secrets panel: reads a gitignored .env file
# into the process environment, so the key never lives in source code.
# Explicit path, not cwd-dependent auto-discovery — this file's location
# relative to the project root is fixed, whereas the process's actual
# working directory depends on how/where uvicorn was launched from.
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def get_anthropic_client():
    """FastAPI dependency. Tests override this with a fake client so the
    test suite never makes a real (paid, non-deterministic) API call."""
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
