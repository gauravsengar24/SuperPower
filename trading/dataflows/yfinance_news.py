from __future__ import annotations

"""Yahoo Finance news fetching with look-ahead filtering."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import yfinance as yf
import requests
from parsel import Selector

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def get_news(symbol: str, curr_date: str, limit: int = 20) -> list[dict]:
    """Fetch news for a ticker, filtered to avoid look-ahead bias."""
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news or []
        articles = [_extract_article_data(a) for a in news[:limit]]
        return _filter_lookahead(articles, curr_date)
    except Exception as e:
        logger.warning("News fetch error for %s: %s", symbol, e)
        return []


def get_global_news(queries: list[str], limit: int = 10,
                    lookback_days: int = 7) -> list[dict]:
    """Fetch global macro news from RSS feeds."""
    all_news = []
    seen_titles = set()
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=lookback_days)

    # BUG FIX: Collect all articles from ALL queries before truncating to limit
    for query in queries:
        if len(all_news) >= limit * 2:
            break
        try:
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=10)
            if resp.status_code != 200:
                continue
            sel = Selector(text=resp.text)
            for item in sel.css("item"):
                title = item.css("title::text").get("").strip()
                if title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())
                pub_date_str = item.css("pubDate::text").get("")
                pub_date = _parse_date(pub_date_str) if pub_date_str else None
                if pub_date and (pub_date < start_date or pub_date > end_date):
                    continue
                link = item.css("link::text").get("")
                desc = item.css("description::text").get("")[:300]
                all_news.append({
                    "title": title,
                    "date": pub_date_str,
                    "source": "Google News",
                    "url": link,
                    "summary": desc,
                })
        except Exception as e:
            logger.warning("Global news fetch error for query %s: %s", query, e)
            continue

    # Now truncate to limit (after collecting from all queries)
    return all_news[:limit]


def _extract_article_data(article: dict) -> dict:
    return {
        "title": article.get("title", ""),
        "date": article.get("providerPublishTime", ""),
        "source": article.get("publisher", ""),
        "summary": article.get("summary", "")[:500],
        "link": article.get("link", {}).get("href") if isinstance(article.get("link"), dict) else "",
    }


def _filter_lookahead(articles: list[dict], curr_date: str) -> list[dict]:
    try:
        cutoff = datetime.strptime(curr_date, "%Y-%m-%d")
        return [a for a in articles if _article_date(a) <= cutoff]
    except Exception:
        return articles


def _article_date(article: dict) -> datetime:
    d = article.get("date", "")
    if isinstance(d, (int, float)):
        return datetime.fromtimestamp(d, tz=timezone.utc)
    try:
        return datetime.strptime(str(d), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _parse_date(date_str: str) -> datetime | None:
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None
