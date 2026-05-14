from __future__ import annotations

CORE_MARKET_UNIVERSE = [
    "NVDA",
    "AMD",
    "MRVL",
    "AVGO",
    "SMCI",
    "PLTR",
    "CRWV",
    "AI",
    "IONQ",
    "RGTI",
    "QBTS",
    "QUBT",
    "AMPX",
    "ASTS",
    "RKLB",
    "MSTR",
    "COIN",
    "MARA",
    "RIOT",
    "TSLA",
    "ARM",
    "SOUN",
    "BBAI",
    "HOOD",
    "SOFI",
    "UPST",
    "AFRM",
    "CVNA",
    "APP",
    "NET",
    "DDOG",
    "SNOW",
    "SHOP",
    "SPY",
    "QQQ",
    "IWM",
    "VOO",
    "FBTC",
    "VOLT",
    "REMX",
]

ETF_TICKERS = {"SPY", "QQQ", "IWM", "VOO", "FBTC", "VOLT", "REMX"}

SOCIAL_MOMENTUM_UNIVERSE = [
    "NVDA",
    "TSLA",
    "PLTR",
    "SOFI",
    "HOOD",
    "MSTR",
    "COIN",
    "IONQ",
    "RGTI",
    "QBTS",
    "QUBT",
    "AMPX",
    "ASTS",
    "RKLB",
    "CRWV",
    "AI",
    "SOUN",
    "BBAI",
    "MARA",
    "RIOT",
    "GME",
    "AMC",
    "CVNA",
    "UPST",
    "AFRM",
]


def market_universe(include_etfs: bool = True, extra_tickers: list[str] | None = None) -> list[str]:
    seen = set()
    output = []
    for ticker in [*(extra_tickers or []), *CORE_MARKET_UNIVERSE]:
        symbol = str(ticker or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        if not include_etfs and symbol in ETF_TICKERS:
            continue
        seen.add(symbol)
        output.append(symbol)
    return output
