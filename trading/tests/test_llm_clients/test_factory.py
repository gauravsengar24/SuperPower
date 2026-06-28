"""Tests for LLM client factory."""

import pytest

from trading.llm_clients.factory import (
    create_llm_client, _resolve_provider, OPENAI_COMPATIBLE_PROVIDERS,
)


def test_resolve_openai():
    assert _resolve_provider("openai") == "openai"


def test_resolve_anthropic():
    assert _resolve_provider("anthropic") == "anthropic"


def test_resolve_google():
    assert _resolve_provider("google") == "google"


def test_resolve_openai_compatible():
    for p in ("deepseek", "groq", "mistral", "ollama", "openrouter"):
        assert _resolve_provider(p) == "openai", f"{p} should map to openai"


def test_create_openai_client():
    client = create_llm_client("openai", "gpt-4", temperature=0.5)
    assert client.model == "gpt-4"
    assert client.kwargs.get("temperature") == 0.5


def test_create_anthropic_client():
    client = create_llm_client("anthropic", "claude-3-opus", temperature=0.3)
    assert client.model == "claude-3-opus"


def test_create_google_client():
    client = create_llm_client("google", "gemini-pro")
    assert client.model == "gemini-pro"


def test_create_deepseek_client():
    client = create_llm_client("deepseek", "deepseek-chat", base_url="https://api.deepseek.com")
    assert client.model == "deepseek-chat"
    assert client.base_url == "https://api.deepseek.com"


def test_create_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        create_llm_client("nonexistent_provider", "model")


def test_provider_case_insensitive():
    assert _resolve_provider("OpenAI") == "openai"
    assert _resolve_provider("ANTHROPIC") == "anthropic"


def test_all_openai_compatible():
    assert "deepseek" in OPENAI_COMPATIBLE_PROVIDERS
    assert "ollama" in OPENAI_COMPATIBLE_PROVIDERS
    assert "openai" not in OPENAI_COMPATIBLE_PROVIDERS
