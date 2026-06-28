"""Tests for symbol utilities."""

import pytest
from trading.dataflows.symbol_utils import normalize_symbol, is_yahoo_safe


class TestNormalizeSymbol:
    def test_stock_passthrough(self):
        assert normalize_symbol("AAPL") == "AAPL"

    def test_crypto_mapping(self):
        assert normalize_symbol("BTC") == "BTC-USD"
        assert normalize_symbol("ETH") == "ETH-USD"

    def test_commodity_mapping(self):
        assert normalize_symbol("XAUUSD") == "GC=F"
        assert normalize_symbol("XAGUSD") == "SI=F"

    def test_index_mapping(self):
        assert normalize_symbol("VIX") == "^VIX"
        assert normalize_symbol("SPX") == "^GSPC"


class TestIsYahooSafe:
    def test_safe_symbols(self):
        assert is_yahoo_safe("AAPL")
        assert is_yahoo_safe("BTC-USD")
        assert is_yahoo_safe("0700.HK")

    def test_unsafe_symbols(self):
        assert not is_yahoo_safe("../etc/passwd")
        assert not is_yahoo_safe("../../secret")
