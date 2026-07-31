import os

from anthropic import Anthropic
from dotenv import load_dotenv

# Local equivalent of Colab's Secrets panel: reads a gitignored .env file
# into the process environment, so the key never lives in source code.
load_dotenv()


def get_anthropic_client():
    """FastAPI dependency. Tests override this with a fake client so the
    test suite never makes a real (paid, non-deterministic) API call."""
    return Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
