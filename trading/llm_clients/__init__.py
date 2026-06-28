"""Q.U.A.N.T. — Quantitative User Assistant for Network Trading
Multi-provider LLM factory supporting 14+ providers with cost-optimized routing.
"""

from .factory import create_llm_client

__all__ = ["create_llm_client"]
