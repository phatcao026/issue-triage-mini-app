"""Shared configuration for the Buổi 02 executable demos."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIRECTORY.parents[2]


def load_environment() -> None:
    """Load optional repository- and demo-local .env files without overriding OS env."""
    load_dotenv(REPOSITORY_ROOT / ".env")
    load_dotenv(SCRIPT_DIRECTORY / ".env")


def model_name() -> str:
    load_environment()
    model = os.getenv("OPENAI_MODEL")
    if not model:
        raise RuntimeError(
            "OPENAI_MODEL is required. Set a model ID offered by the configured provider."
        )
    return model


def openai_client() -> OpenAI:
    """Create a client for the configured OpenAI-compatible API endpoint."""
    load_environment()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required. Copy .env.example to .env and set the key."
        )
    if not base_url:
        raise RuntimeError(
            "OPENAI_BASE_URL is required. Set the OpenAI-compatible API base URL in .env."
        )
    return OpenAI(api_key=api_key, base_url=base_url)
