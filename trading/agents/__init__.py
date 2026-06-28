# MATRIX — Multi-Agent Analysis Orchestration
from .analysts.market_analyst import create_market_analyst
from .analysts.sentiment_analyst import create_sentiment_analyst
from .analysts.news_analyst import create_news_analyst
from .analysts.fundamentals_analyst import create_fundamentals_analyst
from .researchers.bull_researcher import create_bull_researcher
from .researchers.bear_researcher import create_bear_researcher
from .managers.research_manager import create_research_manager
from .managers.portfolio_manager import create_portfolio_manager
from .trader.trader import create_trader
from .risk_mgmt.aggressive_debator import create_aggressive_debator
from .risk_mgmt.conservative_debator import create_conservative_debator
from .risk_mgmt.neutral_debator import create_neutral_debator
from .utils.agent_utils import create_msg_delete

__all__ = [
    "create_market_analyst",
    "create_sentiment_analyst",
    "create_news_analyst",
    "create_fundamentals_analyst",
    "create_bull_researcher",
    "create_bear_researcher",
    "create_research_manager",
    "create_portfolio_manager",
    "create_trader",
    "create_aggressive_debator",
    "create_conservative_debator",
    "create_neutral_debator",
    "create_msg_delete",
]
