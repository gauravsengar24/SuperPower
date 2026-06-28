"""Tests for signal processing."""

import pytest
from trading.agents.utils.signal import parse_rating, SignalProcessor


class TestParseRating:
    def test_strong_buy(self):
        assert parse_rating("STRONG BUY") == "STRONG_BUY"

    def test_buy(self):
        assert parse_rating("BUY") == "BUY"

    def test_hold(self):
        assert parse_rating("HOLD") == "HOLD"

    def test_sell(self):
        assert parse_rating("SELL") == "SELL"

    def test_strong_sell(self):
        assert parse_rating("STRONG SELL") == "STRONG_SELL"

    def test_empty_returns_hold(self):
        assert parse_rating("") == "HOLD"

    def test_case_insensitive(self):
        assert parse_rating("strong buy") == "STRONG_BUY"

    def test_embedded_in_text(self):
        assert parse_rating("Based on analysis, I recommend a BUY for AAPL") == "BUY"

    def test_json_format(self):
        assert parse_rating('{"rating": "SELL", "confidence": 0.8}') == "SELL"

    def test_unknown_returns_hold(self):
        assert parse_rating("UNCLEAR SIGNAL") == "HOLD"


class TestSignalProcessor:
    def test_process_signal(self):
        sp = SignalProcessor()
        assert sp.process_signal("BUY") == "BUY"
        assert sp.process_signal("STRONG SELL") == "STRONG_SELL"
