"""Tests for TREND monitoring module."""

from trading.monitoring.trend import TREND


def test_init():
    t = TREND()
    assert t.current_provider == "openai"
    s = t.get_summary()
    assert s["total_calls"] == 0
    assert s["total_errors"] == 0


def test_record_success():
    t = TREND()
    t.record_call("openai", "gpt-4", 500, True, 100)
    s = t.get_summary()
    assert s["total_calls"] == 1
    assert s["total_errors"] == 0


def test_record_failure():
    t = TREND()
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    s = t.get_summary()
    assert s["total_calls"] == 1
    assert s["total_errors"] == 1


def test_fallback_after_threshold():
    t = TREND(config={"error_threshold": 2})
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    assert t.current_provider == "openai"
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    assert t.current_provider == "anthropic"


def test_fallback_chain():
    t = TREND(config={
        "provider_fallback_chain": ["openai", "anthropic", "google"],
        "error_threshold": 1,
    })
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    assert t.current_provider == "anthropic"
    t.record_call("anthropic", "claude-3", 0, False, error="timeout")
    assert t.current_provider == "google"


def test_fallback_resets_on_success():
    t = TREND(config={"error_threshold": 2})
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    t.record_call("openai", "gpt-4", 100, True)
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    assert t.current_provider == "openai"


def test_all_providers_exhausted():
    t = TREND(config={"provider_fallback_chain": ["openai"], "error_threshold": 1})
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    assert t.current_provider == "openai"


def test_provider_stats():
    t = TREND()
    t.record_call("openai", "gpt-4", 100, True, 50)
    t.record_call("openai", "gpt-4", 200, True, 100)
    stats = t.get_provider_stats("openai")
    assert stats["calls"] == 2
    assert stats["success_rate"] == 1.0
    assert stats["avg_duration_ms"] == 150.0
    assert stats["total_tokens"] == 150


def test_summary():
    t = TREND()
    t.record_call("openai", "gpt-4", 100, True, 50)
    t.record_call("openai", "gpt-4", 0, False, error="timeout")
    s = t.get_summary()
    assert s["total_calls"] == 2
    assert s["total_errors"] == 1
    assert s["current_provider"] == "openai"
    assert len(s["provider_stats"]) == 4
