"""Tests for sentiment_analyst module."""

from trading.agents.analysts.sentiment_analyst import (
    _extract_score, _extract_signals, _extract_confidence,
)


def test_extract_score_bullish():
    assert _extract_score("strong buy signal") == 0.8
    assert _extract_score("very bullish outlook") == 0.8


def test_extract_score_bearish():
    assert _extract_score("strong sell signal") == -0.8
    assert _extract_score("very bearish outlook") == -0.8


def test_extract_score_numeric():
    assert _extract_score("score: 0.75") == 0.75
    assert _extract_score("rating: -0.3") == -0.3


def test_extract_score_clamped():
    assert _extract_score("score: 5.0") == 1.0
    assert _extract_score("score: -10.0") == -1.0


def test_extract_score_neutral():
    assert _extract_score("no clear direction") == 0.0


def test_extract_signals():
    text = "Key signal: rising volume\nSome other text\nkey factor: earnings beat"
    signals = _extract_signals(text)
    assert len(signals) >= 2


def test_extract_signals_fallback():
    assert _extract_signals("nothing relevant here") == ["Sentiment analysis completed"]


def test_extract_confidence():
    assert _extract_confidence("high confidence in this") == "high"
    assert _extract_confidence("confidence: medium") == "medium"
    assert _extract_confidence("low confidence") == "low"


def test_extract_confidence_default():
    assert _extract_confidence("no confidence indicator") == "medium"
