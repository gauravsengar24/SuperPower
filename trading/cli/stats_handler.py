"""LangChain callback handler for tracking LLM call statistics.

BUG-2 FIX: Only implements on_chat_model_start (not on_llm_start).
LangChain fires both for the same chat model call — implementing both
would double the count.
"""

from langchain_core.callbacks import BaseCallbackHandler


class StatsCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        super().__init__()
        self.llm_calls = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.llm_calls += 1

    def on_llm_end(self, response, **kwargs):
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            self.total_tokens += token_usage.get("total_tokens", 0)
            self.prompt_tokens += token_usage.get("prompt_tokens", 0)
            self.completion_tokens += token_usage.get("completion_tokens", 0)

    def get_summary(self):
        return {
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }
