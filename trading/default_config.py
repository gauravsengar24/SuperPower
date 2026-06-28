# SuperTrading AI — Default Configuration
# https://github.com/gauravsengar24/SuperPower

import os

_TRADING_HOME = os.path.join(os.path.expanduser("~"), ".trading")

_ENV_OVERRIDES = {
    "TRADING_LLM_PROVIDER": "llm_provider",
    "TRADING_DEEP_THINK_LLM": "deep_think_llm",
    "TRADING_QUICK_THINK_LLM": "quick_think_llm",
    "TRADING_LLM_BACKEND_URL": "backend_url",
    "TRADING_OUTPUT_LANGUAGE": "output_language",
    "TRADING_MAX_DEBATE_ROUNDS": "max_debate_rounds",
    "TRADING_MAX_RISK_ROUNDS": "max_risk_discuss_rounds",
    "TRADING_CHECKPOINT_ENABLED": "checkpoint_enabled",
    "TRADING_BENCHMARK_TICKER": "benchmark_ticker",
    "TRADING_TEMPERATURE": "temperature",
    "TRADING_GOOGLE_THINKING_LEVEL": "google_thinking_level",
    "TRADING_OPENAI_REASONING_EFFORT": "openai_reasoning_effort",
    "TRADING_ANTHROPIC_EFFORT": "anthropic_effort",
    # Risk gates (AEGIS)
    "TRADING_MAX_POSITIONS": "max_positions",
    "TRADING_MAX_POSITION_PCT": "max_position_pct",
    "TRADING_MAX_DAILY_DRAWDOWN": "max_daily_drawdown",
    "TRADING_MAX_TRAILING_DRAWDOWN": "max_trailing_drawdown",
    "TRADING_VAR_CONFIDENCE": "var_confidence",
    "TRADING_VOLATILITY_THRESHOLD": "volatility_threshold",
    "TRADING_DEFAULT_RISK_PER_TRADE": "default_risk_per_trade",
    # Execution (VELOCITY)
    "TRADING_BROKER": "broker",
    "TRADING_PAPER_TRADING": "paper_trading",
    "TRADING_ALPACA_API_KEY": "alpaca_api_key",
    "TRADING_ALPACA_SECRET_KEY": "alpaca_secret_key",
    "TRADING_ALPACA_BASE_URL": "alpaca_base_url",
    # Dashboard
    "TRADING_DASHBOARD_PORT": "dashboard_port",
    "TRADING_DASHBOARD_HOST": "dashboard_host",
}

_BOOL_TRUE = ("true", "1", "yes", "on")
_BOOL_FALSE = ("false", "0", "no", "off")


def _coerce(value: str, reference):
    if isinstance(reference, bool):
        normalized = value.strip().lower()
        if normalized in _BOOL_TRUE:
            return True
        if normalized in _BOOL_FALSE:
            return False
        raise ValueError(
            f"Expected boolean ({'/'.join(_BOOL_TRUE + _BOOL_FALSE)}), got {value!r}"
        )
    if isinstance(reference, int) and not isinstance(reference, bool):
        return int(value)
    if isinstance(reference, float):
        return float(value)
    return value


def _apply_env_overrides(config: dict) -> dict:
    for env_var, key in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None or raw == "":
            continue
        try:
            config[key] = _coerce(raw, config.get(key))
        except ValueError as exc:
            raise ValueError(f"Invalid value for {env_var}: {exc}") from exc
    return config


DEFAULT_CONFIG = _apply_env_overrides({
    "project_dir": os.path.abspath(os.path.dirname(__file__)),
    "results_dir": os.getenv("TRADING_RESULTS_DIR", os.path.join(_TRADING_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADING_CACHE_DIR", os.path.join(_TRADING_HOME, "cache")),
    "memory_log_path": os.getenv(
        "TRADING_MEMORY_LOG_PATH",
        os.path.join(_TRADING_HOME, "memory", "trading_memory.md"),
    ),
    "memory_log_max_entries": None,
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.5",
    "quick_think_llm": "gpt-5.4-mini",
    "backend_url": None,
    "google_thinking_level": None,
    "openai_reasoning_effort": None,
    "anthropic_effort": None,
    "temperature": None,
    "checkpoint_enabled": False,
    "output_language": "English",
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    "news_article_limit": 20,
    "global_news_article_limit": 10,
    "global_news_lookback_days": 7,
    "global_news_queries": [
        "Federal Reserve interest rates inflation",
        "S&P 500 earnings GDP economic outlook",
        "geopolitical risk trade war sanctions",
        "ECB Bank of England BOJ central bank policy",
        "oil commodities supply chain energy",
    ],
    "data_vendors": {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "yfinance",
        "macro_data": "fred",
        "prediction_markets": "polymarket",
    },
    "tool_vendors": {},
    "benchmark_ticker": None,
    "benchmark_map": {
        ".NS": "^NSEI",
        ".BO": "^BSESN",
        ".T": "^N225",
        ".HK": "^HSI",
        ".L": "^FTSE",
        ".TO": "^GSPTSE",
        ".AX": "^AXJO",
        ".SS": "000001.SS",
        ".SZ": "399001.SZ",
        "": "SPY",
    },
    # AEGIS risk defaults
    "max_positions": 10,
    "max_position_pct": 0.25,
    "max_daily_drawdown": 0.05,
    "max_trailing_drawdown": 0.15,
    "var_confidence": 0.95,
    "volatility_threshold": 0.40,
    "default_risk_per_trade": 0.02,
    # VELOCITY execution defaults
    "broker": "paper",
    "paper_trading": True,
    "alpaca_api_key": None,
    "alpaca_secret_key": None,
    "alpaca_base_url": "https://paper-api.alpaca.markets",
    # Dashboard defaults
    "dashboard_port": 8501,
    "dashboard_host": "0.0.0.0",
})
