"""Trading mode capabilities for Amanah Trader."""

from config import load_settings


AGENT_TEAM = [
    {"name": "Shariah Research", "role": "Compliance universe and evidence"},
    {"name": "Market Data", "role": "Prices, history, and market context"},
    {"name": "Quant Strategy", "role": "Signals and strategy rules"},
    {"name": "Risk Manager", "role": "Hard limits and exposure controls"},
    {"name": "Portfolio Manager", "role": "Watchlist and allocation workflow"},
    {"name": "Execution", "role": "Paper execution behind locks"},
    {"name": "Audit Compliance", "role": "Decision and action trail"},
]


def mode_capabilities(mode: str) -> dict:
    capabilities = {
        "advisory": {
            "agents_can_recommend": True,
            "human_approval_required": False,
            "paper_execution_allowed": False,
            "autonomous_execution_allowed": False,
        },
        "approval": {
            "agents_can_recommend": True,
            "human_approval_required": True,
            "paper_execution_allowed": True,
            "autonomous_execution_allowed": False,
        },
        "autonomous_paper": {
            "agents_can_recommend": True,
            "human_approval_required": False,
            "paper_execution_allowed": True,
            "autonomous_execution_allowed": True,
        },
    }
    return capabilities[mode]


def trading_mode_status() -> dict:
    settings = load_settings()
    capabilities = mode_capabilities(settings.trading_mode)
    broker_submission = settings.paper_execution_enabled and settings.paper_execution_adapter in {"fake", "moomoo"}
    return {
        "trading_mode": settings.trading_mode,
        "paper_execution_enabled": settings.paper_execution_enabled,
        "paper_execution_adapter": settings.paper_execution_adapter,
        "effective_paper_execution_allowed": capabilities["paper_execution_allowed"] and settings.paper_execution_enabled,
        "capabilities": capabilities,
        "agent_team": AGENT_TEAM,
        "live_trading": False,
        "broker_submission": broker_submission,
    }
