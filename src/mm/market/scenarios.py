"""Named market presets. They differ only in the share of informed takers."""

from mm.market.config import MarketConfig

SCENARIOS: dict[str, MarketConfig] = {
    "no_informed": MarketConfig(informed_share=0.0),
    "base": MarketConfig(informed_share=0.15),
    "toxic": MarketConfig(informed_share=0.40),
}
