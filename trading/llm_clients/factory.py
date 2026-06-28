from __future__ import annotations

"""LLM client factory — routes provider string to the correct client implementation."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Registry of OpenAI-compatible providers that share the same client path
OPENAI_COMPATIBLE_PROVIDERS = {
    "deepseek", "groq", "mistral", "nvidia", "kimi", "openrouter",
    "openai_compatible", "ollama", "minimax",
}


def create_llm_client(provider: str, model: str, base_url: str | None = None,
                      **kwargs) -> Any:
    """Create an LLM client for the given provider.

    Args:
        provider: Provider name (openai, anthropic, google, deepseek, etc.)
        model: Model name/ID
        base_url: Optional custom base URL
        **kwargs: Additional provider-specific args (temperature, thinking_level, etc.)

    Returns:
        LLM client instance with .get_llm() method
    """
    provider = provider.lower().strip()
    client_type = _resolve_provider(provider)

    if client_type == "openai":
        from .openai_client import OpenAIClient
        return OpenAIClient(model=model, base_url=base_url, **kwargs)

    elif client_type == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(model=model, base_url=base_url, **kwargs)

    elif client_type == "google":
        from .google_client import GoogleClient
        return GoogleClient(model=model, base_url=base_url, **kwargs)

    elif client_type == "azure":
        from .azure_client import AzureOpenAIClient
        return AzureOpenAIClient(model=model, base_url=base_url, **kwargs)

    elif client_type == "bedrock":
        from .bedrock_client import BedrockClient
        return BedrockClient(model=model, **kwargs)

    else:
        raise ValueError(f"Unknown provider: {provider}")


def _resolve_provider(provider: str) -> str:
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return "openai"
    return provider


# Stub clients for providers that require optional dependencies


class _StubOpenAI:
    """Minimal OpenAI client for when langchain-openai is not installed."""

    def __init__(self, model, base_url=None, **kwargs):
        self.model = model
        self.base_url = base_url
        self.kwargs = kwargs

    def get_llm(self):
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=self.model,
                base_url=self.base_url,
                **self.kwargs,
            )
        except ImportError:
            raise ImportError(
                "langchain-openai is required. Install: pip install langchain-openai"
            )


class OpenAIClient(_StubOpenAI):
    pass


class AnthropicClient:
    def __init__(self, model, base_url=None, **kwargs):
        self.model = model
        self.base_url = base_url
        self.kwargs = kwargs

    def get_llm(self):
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=self.model,
                base_url=self.base_url,
                **{k: v for k, v in self.kwargs.items() if k != "reasoning_effort"},
            )
        except ImportError:
            raise ImportError(
                "langchain-anthropic is required. Install: pip install langchain-anthropic"
            )


class GoogleClient:
    def __init__(self, model, base_url=None, **kwargs):
        self.model = model
        self.base_url = base_url
        self.kwargs = kwargs

    def get_llm(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=self.model,
                **self.kwargs,
            )
        except ImportError:
            raise ImportError(
                "langchain-google-genai is required. Install: pip install langchain-google-genai"
            )


class AzureOpenAIClient:
    def __init__(self, model, base_url=None, **kwargs):
        self.model = model
        self.kwargs = kwargs

    def get_llm(self):
        try:
            from langchain_openai import AzureChatOpenAI
            return AzureChatOpenAI(
                model=self.model,
                azure_deployment=self.model,
                **self.kwargs,
            )
        except ImportError:
            raise ImportError("langchain-openai required for Azure")


class BedrockClient:
    def __init__(self, model, **kwargs):
        self.model = model
        self.kwargs = kwargs

    def get_llm(self):
        try:
            from langchain_aws import ChatBedrock
            return ChatBedrock(model_id=self.model, **self.kwargs)
        except ImportError:
            raise ImportError(
                "langchain-aws is required for Bedrock. Install: pip install 'trading[bedrock]'"
            )
