"""Tests for trader module."""

from trading.agents.trader.trader import _parse_trader_proposal


def test_parse_buy():
    text = "Side: BUY\nOrder type: MARKET\nQuantity: 100\nConfidence: 0.85\nReasoning: Strong momentum"
    prop = _parse_trader_proposal("AAPL", text)
    assert prop.ticker == "AAPL"
    assert prop.side == "BUY"
    assert prop.order_type == "MARKET"
    assert prop.quantity == 100
    assert prop.confidence_score == 0.85


def test_parse_sell_limit():
    text = "Side: SELL\nOrder type: LIMIT\nQuantity: 50\nLimit price: 155.00\nConfidence: 0.7"
    prop = _parse_trader_proposal("TSLA", text)
    assert prop.side == "SELL"
    assert prop.order_type == "LIMIT"
    assert prop.quantity == 50
    assert prop.limit_price == 155.0
    assert prop.confidence_score == 0.7


def test_parse_stop():
    text = "Sell\nstop order\nquantity: 200\nstop price: 140.00\nconfidence: 0.9"
    prop = _parse_trader_proposal("MSFT", text)
    assert prop.side == "SELL"
    assert prop.order_type == "STOP"
    assert prop.stop_price == 140.0


def test_parse_defaults():
    prop = _parse_trader_proposal("UNKNOWN", "")
    assert prop.side == "HOLD"
    assert prop.quantity == 100
    assert prop.confidence_score == 0.5


def test_confidence_clamped():
    prop = _parse_trader_proposal("TEST", "confidence: 5.0")
    assert prop.confidence_score == 1.0
    prop2 = _parse_trader_proposal("TEST", "confidence: -1.0")
    assert prop2.confidence_score == 0.0
