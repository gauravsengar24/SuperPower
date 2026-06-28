"""Pydantic models for structured agent output."""

from pydantic import BaseModel, Field
from typing import Optional


class SentimentReport(BaseModel):
    overall_sentiment: str = Field(description="Overall sentiment: bullish/bearish/neutral")
    sentiment_score: float = Field(description="Score from -1 (very bearish) to +1 (very bullish)")
    key_signals: list[str] = Field(description="Key signals driving sentiment")
    confidence: str = Field(description="Confidence in assessment: high/medium/low")


class ResearchPlan(BaseModel):
    ticker: str = Field(description="Ticker symbol")
    direction: str = Field(description="Trading direction: LONG/SHORT/NEUTRAL")
    entry_price_range: str = Field(description="Suggested entry price range")
    stop_loss: float = Field(description="Stop loss price level")
    take_profit: float = Field(description="Take profit price level")
    confidence: str = Field(description="Confidence: HIGH/MEDIUM/LOW")
    reasoning: str = Field(description="Detailed reasoning for the plan")
    risk_factors: list[str] = Field(description="Key risk factors")
    catalysts: list[str] = Field(description="Potential catalysts")


class TraderProposal(BaseModel):
    ticker: str = Field(description="Ticker symbol")
    side: str = Field(description="BUY or SELL")
    order_type: str = Field(description="MARKET, LIMIT, STOP")
    quantity: int = Field(description="Number of shares")
    limit_price: Optional[float] = Field(None, description="Limit price if applicable")
    stop_price: Optional[float] = Field(None, description="Stop price if applicable")
    confidence_score: float = Field(description="Confidence 0.0-1.0")
    reasoning: str = Field(description="Detailed reasoning")


class PortfolioDecision(BaseModel):
    approved: bool = Field(description="Whether to approve the trade proposal")
    position_size_modification: Optional[str] = Field(None, description="Size change suggestion")
    risk_notes: str = Field(description="Risk management notes")
    final_verdict: str = Field(description="FINAL APPROVED/REJECTED/MODIFIED")
