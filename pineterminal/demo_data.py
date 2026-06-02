from __future__ import annotations

from collections import Counter

from pineterminal.calculations import (
    calculate_expected_return,
    calculate_expected_value_detail,
    calculate_fundamental_score,
    calculate_future_share_price,
    calculate_future_value_bridge,
    calculate_investment_signal,
    calculate_net_readthrough_score,
    classify_business_quality,
    classify_investment_signal,
    generate_signal_summary,
    get_theme_read_through_for_ticker,
    with_market_implied_conclusion,
)
from pineterminal.types import (
    Company,
    CompanyAnalysis,
    FundamentalMetric,
    FutureValueBridgeItem,
    InvestmentSignal,
    MarketImpliedAssumptions,
    MarketReadThroughItem,
    RiskItem,
    SensitivityTable,
    ThemeExposure,
    ThesisChangeSummary,
    ThesisUpdate,
    ValuationScenario,
    WhatMustBeTrueItem,
)
from pineterminal.valuation import format_financial_value, get_valuation_model


FUNDAMENTAL_WEIGHTS = {
    "Revenue Growth": 0.35,
    "Gross Margin": 0.15,
    "Operating Leverage": 0.12,
    "Free Cash Flow": 0.05,
    "Balance Sheet": 0.12,
    "Customers / Backlog": 0.11,
    "Competitive Position": 0.05,
    "Execution Quality": 0.05,
}


COMPANIES: dict[str, Company] = {
    "AMPX": Company("AMPX", "Amprius Technologies, Inc.", "Industrials", "Electrical Equipment & Parts", ["Batteries", "Silicon Anode", "Military Drones", "EVs", "High-Density Energy Storage"], 20.28, -2.73, 2_872_200_000, 2_816_400_000, 2.55, 22.80, pre_market_change_percent=0.0, after_hours_change_percent=0.0, market_status="Closed", last_updated="2026-06-01 05:54 ET", data_mode="Live Fallback", data_source="Yahoo Finance/yfinance + SEC XBRL fallback", revenue_ttm=90_000_000, gross_margin=20.1, cash=62_352_000, debt=6_562_000, day_change_dollar=-0.57, shares_outstanding=141_627_170, cash_burn_ttm=-38_255_000),
    "MRVL": Company("MRVL", "Marvell Technology, Inc.", "Technology", "Semiconductors", ["AI Data Centers", "Custom Silicon", "Networking", "Optical Connectivity"], 68.32, 2.11, 59_200_000_000, 61_600_000_000, 47.09, 127.48, pre_market_change_percent=0.4, after_hours_change_percent=0.2, revenue_ttm=5_600_000_000, gross_margin=47, cash=950_000_000, debt=4_100_000_000),
    "IONQ": Company("IONQ", "IonQ, Inc.", "Technology", "Quantum Computing", ["Quantum Computing", "Long-Duration Growth", "Government R&D", "Speculative Technology"], 18.67, -1.02, 4_100_000_000, 3_650_000_000, 6.22, 54.74, pre_market_change_percent=-0.6, after_hours_change_percent=-0.4, revenue_ttm=45_000_000, gross_margin=54, cash=420_000_000, debt=0),
    "MP": Company("MP", "MP Materials Corp.", "Materials", "Rare Earths", ["Critical Minerals", "Rare Earths", "Defense Supply Chain", "Reshoring"], 25.11, 1.76, 4_300_000_000, 4_000_000_000, 10.02, 29.88, pre_market_change_percent=0.2, after_hours_change_percent=0.1, revenue_ttm=238_000_000, gross_margin=22, cash=997_000_000, debt=930_000_000),
    "VICR": Company("VICR", "Vicor Corporation", "Technology", "Power Electronics", ["Power Electronics", "Components", "Margin Recovery", "Industrial Power"], 44.00, 0.0, 1_950_000_000, 1_700_000_000, 28.00, 72.00, pre_market_change_percent=0.0, after_hours_change_percent=0.0, revenue_ttm=360_000_000, gross_margin=46, cash=280_000_000, debt=30_000_000, shares_outstanding=44_000_000),
    "FBTC": Company("FBTC", "Fidelity Wise Origin Bitcoin Fund", "Digital Assets", "Bitcoin ETF", ["Bitcoin", "Crypto ETF Flows", "Digital Assets", "Liquidity"], 59.42, 3.34, 23_500_000_000, 23_500_000_000, 38.10, 71.20, pre_market_change_percent=1.1, after_hours_change_percent=0.5, revenue_ttm=None, gross_margin=None, cash=None, debt=None),
    "NVDA": Company("NVDA", "NVIDIA Corporation", "Technology", "Semiconductors", ["AI Compute", "GPUs", "AI Data Centers", "Accelerated Computing"], 985.97, 1.14, 2_430_000_000_000, 2_390_000_000_000, 756.34, 1261.33, pre_market_change_percent=0.7, after_hours_change_percent=0.3, revenue_ttm=130_500_000_000, gross_margin=73, cash=34_800_000_000, debt=9_700_000_000),
    "CEG": Company("CEG", "Constellation Energy Corporation", "Utilities", "Nuclear Power", ["Power Demand", "Nuclear Energy", "AI Data Centers", "Grid Demand"], 301.21, 2.08, 93_500_000_000, 101_200_000_000, 158.12, 326.44, pre_market_change_percent=0.3, after_hours_change_percent=0.1, revenue_ttm=24_900_000_000, gross_margin=41, cash=2_300_000_000, debt=9_800_000_000),
}


THEME_EXPOSURES = [
    ThemeExposure("Military Drones", ["AMPX", "AVAV", "RCAT", "KTOS"], "Higher drone demand increases need for lightweight, high-density batteries, sensors, and autonomous systems.", "Positive", ["Revenue Growth"], "2026-05-20", "12-36 months"),
    ThemeExposure("Batteries", ["AMPX", "QS", "SLDP", "ALB"], "Battery supply chain funding and qualification cycles affect demand for advanced cell chemistries.", "Positive", ["Revenue Growth", "Gross Margin"], "2026-05-19", "12-36 months"),
    ThemeExposure("EVs", ["AMPX", "TSLA", "RIVN", "ALB"], "EV demand shifts influence battery supplier growth assumptions and investor appetite.", "Neutral", ["Revenue Growth"], "2026-05-18", "12-36 months"),
    ThemeExposure("Rates / Treasury Yields", ["IONQ", "AMPX", "FBTC", "Growth Stocks", "Long Duration Tech"], "Higher discount rates reduce present value of future cash flows.", "Negative", ["Multiple Compression", "Discount Rate"], "2026-05-18", "0-18 months"),
    ThemeExposure("AI Data Centers", ["MRVL", "NVDA", "DELL", "HPE", "VRT", "CEG"], "Higher hyperscaler capex supports demand for networking, servers, cooling, power, and custom silicon.", "Positive", ["Revenue Growth", "Multiple Expansion"], "2026-05-20", "6-36 months"),
    ThemeExposure("Custom Silicon", ["MRVL", "AVGO", "NVDA", "TSM"], "ASIC demand can shift semiconductor revenue mix toward higher-value AI workloads.", "Positive", ["Revenue Growth", "Gross Margin"], "2026-05-20", "12-36 months"),
    ThemeExposure("Networking", ["MRVL", "ANET", "CSCO", "NVDA"], "AI clusters require faster optical and switching fabrics as model sizes grow.", "Positive", ["Revenue Growth"], "2026-05-17", "6-24 months"),
    ThemeExposure("Semiconductor Cycle", ["MRVL", "NVDA", "AMD", "TSM"], "Inventory corrections or export controls can pressure chip demand and multiples.", "Negative", ["Revenue Growth", "Multiple Compression"], "2026-05-16", "0-18 months"),
    ThemeExposure("Critical Minerals", ["MP", "REMX", "LAC"], "Supply chain restrictions increase strategic value of domestic rare earth and critical mineral assets.", "Positive", ["Multiple Expansion"], "2026-05-19", "12-48 months"),
    ThemeExposure("Rare Earths", ["MP", "REMX", "LYC"], "Rare earth pricing and magnet demand drive revenue sensitivity for miners and processors.", "Neutral", ["Revenue Growth", "Gross Margin"], "2026-05-18", "6-36 months"),
    ThemeExposure("Defense Supply Chain", ["MP", "AMPX", "LMT", "RTX"], "Defense procurement priorities increase strategic value for domestic suppliers with scarce inputs or enabling technology.", "Positive", ["Customer Demand", "Multiple Expansion"], "2026-05-17", "12-48 months"),
    ThemeExposure("Reshoring", ["MP", "LAC", "X", "NUE"], "Policy support for domestic supply chains can lower funding risk and improve strategic value.", "Positive", ["Balance Sheet Risk", "Multiple Expansion"], "2026-05-17", "12-48 months"),
    ThemeExposure("Bitcoin", ["FBTC", "MSTR", "COIN", "MARA", "RIOT"], "Bitcoin price movement directly affects crypto-linked asset values and fund demand.", "Positive", ["Asset Price"], "2026-05-20", "0-12 months"),
    ThemeExposure("Crypto ETF Flows", ["FBTC", "COIN", "MSTR", "MARA", "RIOT"], "ETF inflows and Bitcoin price movement affect crypto-linked equities and funds.", "Positive", ["Asset Price", "Multiple Expansion"], "2026-05-19", "0-18 months"),
    ThemeExposure("Digital Assets", ["FBTC", "COIN", "MSTR"], "Regulation and institutional allocation influence digital asset liquidity and risk appetite.", "Neutral", ["Customer Demand", "Risk Premium"], "2026-05-18", "0-24 months"),
    ThemeExposure("Liquidity", ["FBTC", "MSTR", "Speculative Assets"], "Market liquidity changes the appetite for volatile, duration-sensitive assets.", "Negative", ["Risk Premium"], "2026-05-18", "0-12 months"),
    ThemeExposure("Quantum Computing", ["IONQ", "RGTI", "QBTS", "QUBT"], "Enterprise pilots and technical milestones affect confidence in commercial quantum demand.", "Positive", ["Revenue Growth"], "2026-05-17", "24-60 months"),
    ThemeExposure("Government R&D", ["IONQ", "LMT", "RTX", "BAH"], "Government research funding can validate emerging technologies and extend cash runway.", "Positive", ["Customer Demand", "Balance Sheet Risk"], "2026-05-17", "12-48 months"),
    ThemeExposure("Speculative Technology", ["IONQ", "AMPX", "RGTI", "Long Duration Tech"], "Risk appetite determines whether investors pay for distant revenue and optionality.", "Neutral", ["Multiple Expansion", "Multiple Compression"], "2026-05-16", "0-18 months"),
    ThemeExposure("AI Compute", ["NVDA", "AMD", "AVGO", "TSM"], "AI training and inference demand supports GPU, accelerator, and platform revenue.", "Positive", ["Revenue Growth", "Gross Margin"], "2026-05-20", "6-36 months"),
    ThemeExposure("GPUs", ["NVDA", "AMD", "SMCI"], "GPU supply, pricing, and utilization shape AI platform revenue durability.", "Positive", ["Gross Margin", "Revenue Growth"], "2026-05-19", "6-24 months"),
    ThemeExposure("Power Demand", ["CEG", "VST", "NEE", "DUK"], "Data-center load growth increases demand for reliable clean power generation.", "Positive", ["Revenue Growth", "Multiple Expansion"], "2026-05-20", "12-48 months"),
    ThemeExposure("Nuclear Energy", ["CEG", "VST", "CCJ"], "Nuclear power scarcity and clean-energy contracts support durable cash flows.", "Positive", ["Competitive Position", "Multiple Expansion"], "2026-05-19", "12-60 months"),
    ThemeExposure("Grid Demand", ["CEG", "ETN", "PWR", "VRT"], "Grid bottlenecks can lift power pricing but raise execution and policy risk.", "Neutral", ["Revenue Growth", "Execution Risk"], "2026-05-18", "12-48 months"),
]


MARKET_UPDATES = [
    {"date": "2026-05-20", "market_update": "US defense agencies increase funding for small autonomous drones", "theme": "Military Drones", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Drone endurance and battery weight are bottlenecks, supporting high-density battery suppliers.", "affected_valuation_lever": "Revenue Growth", "thesis_impact": "Strengthens demand thesis"},
    {"date": "2026-05-19", "market_update": "Advanced battery tax credit language remains supportive", "theme": "Batteries", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Policy support can reduce customer adoption friction for domestic advanced batteries.", "affected_valuation_lever": "Revenue Growth / Gross Margin", "thesis_impact": "Strengthens manufacturing thesis"},
    {"date": "2026-05-18", "market_update": "EV production plans soften at several automakers", "theme": "EVs", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Slower EV ramps can delay broad battery volume adoption even if defense demand improves.", "affected_valuation_lever": "Revenue Growth", "thesis_impact": "Weakens non-defense growth optionality"},
    {"date": "2026-05-18", "market_update": "10-year Treasury yield moves higher on sticky inflation", "theme": "Rates / Treasury Yields", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Higher rates pressure long-duration growth valuations and raise the required return.", "affected_valuation_lever": "Multiple Compression", "thesis_impact": "Weakens valuation support"},
    {"date": "2026-05-20", "market_update": "Hyperscalers raise AI infrastructure capex guidance", "theme": "AI Data Centers", "impact": "Positive", "confidence": "High", "why_it_matters": "Higher AI capex supports networking, custom silicon, power, and cooling demand.", "affected_valuation_lever": "Revenue Growth / Multiple Expansion", "thesis_impact": "Strengthens AI infrastructure thesis"},
    {"date": "2026-05-20", "market_update": "Large cloud customer signs next-generation ASIC roadmap", "theme": "Custom Silicon", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Custom silicon roadmaps can create durable multi-year semiconductor revenue streams.", "affected_valuation_lever": "Revenue Growth", "thesis_impact": "Strengthens customer demand"},
    {"date": "2026-05-17", "market_update": "Optical interconnect demand improves with larger AI clusters", "theme": "Networking", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Cluster scale increases the need for high-speed optical networking and switching.", "affected_valuation_lever": "Revenue Growth", "thesis_impact": "Strengthens networking growth"},
    {"date": "2026-05-16", "market_update": "Semiconductor inventory digestion persists in non-AI end markets", "theme": "Semiconductor Cycle", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Weak non-AI demand can offset AI growth and pressure blended margins.", "affected_valuation_lever": "Gross Margin / Revenue Growth", "thesis_impact": "Weakens cyclical support"},
    {"date": "2026-05-19", "market_update": "China tightens rare earth export controls", "theme": "Critical Minerals", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Supply chain stress increases strategic value of domestic critical mineral producers.", "affected_valuation_lever": "Multiple Expansion", "thesis_impact": "Strengthens strategic asset value"},
    {"date": "2026-05-18", "market_update": "Rare earth spot prices remain soft despite policy support", "theme": "Rare Earths", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Weak commodity pricing can offset policy enthusiasm and pressure margins.", "affected_valuation_lever": "Gross Margin", "thesis_impact": "Weakens margin outlook"},
    {"date": "2026-05-17", "market_update": "Defense supply chain review favors domestic rare earth inputs", "theme": "Defense Supply Chain", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Defense procurement priorities can increase strategic demand for domestic rare earth and battery suppliers.", "affected_valuation_lever": "Customer Demand / Multiple Expansion", "thesis_impact": "Strengthens strategic demand"},
    {"date": "2026-05-17", "market_update": "US reshoring grants prioritize defense supply chains", "theme": "Reshoring", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Public funding can lower capital intensity for domestic strategic suppliers.", "affected_valuation_lever": "Balance Sheet Risk / Multiple Expansion", "thesis_impact": "Strengthens funding backdrop"},
    {"date": "2026-05-20", "market_update": "Bitcoin price breaks higher as ETF demand accelerates", "theme": "Bitcoin", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Bitcoin price appreciation directly lifts the asset value and demand for spot ETF exposure.", "affected_valuation_lever": "Asset Price", "thesis_impact": "Strengthens asset price momentum"},
    {"date": "2026-05-19", "market_update": "Spot Bitcoin ETFs post fifth consecutive inflow week", "theme": "Crypto ETF Flows", "impact": "Positive", "confidence": "High", "why_it_matters": "Sustained ETF inflows validate institutional allocation and liquidity support.", "affected_valuation_lever": "Asset Price / Multiple Expansion", "thesis_impact": "Strengthens fund demand"},
    {"date": "2026-05-18", "market_update": "Digital asset market awaits new custody rule guidance", "theme": "Digital Assets", "impact": "Neutral", "confidence": "Medium", "why_it_matters": "Regulatory clarity could expand access, while delays can keep risk premiums elevated.", "affected_valuation_lever": "Risk Premium", "thesis_impact": "Keeps regulatory risk in focus"},
    {"date": "2026-05-18", "market_update": "Real yields rise and liquidity-sensitive assets fade", "theme": "Liquidity", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Higher real yields can reduce appetite for volatile crypto exposure.", "affected_valuation_lever": "Risk Premium", "thesis_impact": "Weakens risk appetite"},
    {"date": "2026-05-17", "market_update": "Federal quantum R&D award cycle expands pilot funding", "theme": "Government R&D", "impact": "Positive", "confidence": "Low", "why_it_matters": "Government demand can validate early-stage quantum platforms and extend development runway.", "affected_valuation_lever": "Customer Demand", "thesis_impact": "Strengthens validation path"},
    {"date": "2026-05-17", "market_update": "Enterprise quantum pilots move from research to workflow testing", "theme": "Quantum Computing", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Pilot progression increases confidence that quantum demand is moving beyond lab curiosity.", "affected_valuation_lever": "Revenue Growth", "thesis_impact": "Strengthens adoption thesis"},
    {"date": "2026-05-16", "market_update": "Speculative technology basket underperforms as volatility rises", "theme": "Speculative Technology", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Weak risk appetite reduces the market's willingness to pay for distant optionality.", "affected_valuation_lever": "Multiple Compression", "thesis_impact": "Weakens valuation support"},
    {"date": "2026-05-20", "market_update": "AI model builders expand training and inference GPU clusters", "theme": "AI Compute", "impact": "Positive", "confidence": "High", "why_it_matters": "Sustained AI workload growth supports GPU demand and platform pricing power.", "affected_valuation_lever": "Revenue Growth / Gross Margin", "thesis_impact": "Strengthens AI platform thesis"},
    {"date": "2026-05-19", "market_update": "GPU supply remains tight for latest accelerator generation", "theme": "GPUs", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Supply tightness can preserve pricing and margin strength for leading GPU vendors.", "affected_valuation_lever": "Gross Margin", "thesis_impact": "Strengthens margin durability"},
    {"date": "2026-05-20", "market_update": "Data-center power contracts move to longer duration terms", "theme": "Power Demand", "impact": "Positive", "confidence": "High", "why_it_matters": "Longer power contracts can improve revenue visibility for generators with scarce clean capacity.", "affected_valuation_lever": "Revenue Growth / Multiple Expansion", "thesis_impact": "Strengthens contracted demand"},
    {"date": "2026-05-19", "market_update": "Nuclear generation receives bipartisan reliability support", "theme": "Nuclear Energy", "impact": "Positive", "confidence": "Medium", "why_it_matters": "Policy support reinforces the strategic value of always-on clean power assets.", "affected_valuation_lever": "Multiple Expansion", "thesis_impact": "Strengthens competitive position"},
    {"date": "2026-05-18", "market_update": "Grid interconnection queues remain a bottleneck for new load", "theme": "Grid Demand", "impact": "Negative", "confidence": "Medium", "why_it_matters": "Grid delays can slow customer additions and raise execution complexity.", "affected_valuation_lever": "Execution Risk", "thesis_impact": "Weakens timing confidence"},
]


MARKET_INDICES = [
    {"name": "S&P 500", "ticker": "SPY", "price": "6,125.5", "change": 0.42},
    {"name": "Nasdaq", "ticker": "QQQ", "price": "21,931.2", "change": 0.68},
    {"name": "Dow", "ticker": "DIA", "price": "42,884.9", "change": 0.18},
    {"name": "Russell 2000", "ticker": "IWM", "price": "2,201.3", "change": -0.21},
    {"name": "Bitcoin", "ticker": "BTC", "price": "$112,840", "change": 1.94},
    {"name": "10Y Treasury", "ticker": "US10Y", "price": "4.48%", "change": 0.05},
    {"name": "VIX", "ticker": "VIX", "price": "14.7", "change": -2.20},
]


MARKET_MOVERS = [
    {"ticker": "AMPX", "company": "Amprius Technologies", "price": 12.08, "change": 4.32},
    {"ticker": "FBTC", "company": "Fidelity Bitcoin ETF", "price": 59.42, "change": 3.34},
    {"ticker": "CEG", "company": "Constellation Energy", "price": 301.21, "change": 2.08},
    {"ticker": "MRVL", "company": "Marvell Technology", "price": 68.32, "change": 2.11},
    {"ticker": "NVDA", "company": "NVIDIA", "price": 985.97, "change": 1.14},
    {"ticker": "MP", "company": "MP Materials", "price": 25.11, "change": 1.76},
    {"ticker": "IONQ", "company": "IonQ", "price": 18.67, "change": -1.02},
    {"ticker": "RGTI", "company": "Rigetti Computing", "price": 9.18, "change": -4.86},
    {"ticker": "MSTR", "company": "Strategy", "price": 391.42, "change": -2.74},
    {"ticker": "VRT", "company": "Vertiv Holdings", "price": 98.11, "change": -1.45},
]


UPCOMING_EVENTS = [
    {"ticker": "AMPX", "event": "Earnings (Q2 2025)", "date": "Aug 12, 2025"},
    {"ticker": "AMPX", "event": "Investor Presentation", "date": "Jun 05, 2025"},
    {"ticker": "AMPX", "event": "Battery Tech Conference", "date": "Jun 18, 2025"},
    {"ticker": "MRVL", "event": "AI Infrastructure Update", "date": "Jun 11, 2025"},
    {"ticker": "IONQ", "event": "Quantum Systems Roadmap", "date": "Jun 20, 2025"},
    {"ticker": "MP", "event": "Rare Earths Policy Forum", "date": "Jun 24, 2025"},
    {"ticker": "VICR", "event": "Power Electronics Investor Update", "date": "Jun 19, 2025"},
    {"ticker": "FBTC", "event": "Digital Asset Flows Report", "date": "Jun 07, 2025"},
    {"ticker": "NVDA", "event": "AI Compute Platform Update", "date": "Jun 12, 2025"},
    {"ticker": "CEG", "event": "Power Demand Investor Day", "date": "Jun 26, 2025"},
    {"ticker": "FOMC", "event": "Rate Decision", "date": "Jun 17, 2025"},
]


ECONOMIC_DATA = [
    {"metric": "10Y Treasury", "latest": "4.48%", "trend": "Higher", "impact": "Pressures long-duration growth multiples"},
    {"metric": "Core CPI", "latest": "3.1%", "trend": "Sticky", "impact": "Keeps discount-rate risk elevated"},
    {"metric": "ISM Manufacturing", "latest": "50.6", "trend": "Improving", "impact": "Supports industrial demand cyclicals"},
    {"metric": "Fed Funds", "latest": "4.75%", "trend": "Hold", "impact": "Wait-and-see backdrop for risk assets"},
]


PORTFOLIO_HOLDINGS = [
    {"ticker": "AMPX", "weight": 6.0, "signal": "Speculative Buy", "risk": "High", "theme": "Batteries"},
    {"ticker": "MRVL", "weight": 12.0, "signal": "Buy", "risk": "Medium", "theme": "AI Data Centers"},
    {"ticker": "CEG", "weight": 9.0, "signal": "Buy", "risk": "Medium", "theme": "Power Demand"},
    {"ticker": "FBTC", "weight": 7.5, "signal": "Speculative Buy", "risk": "High", "theme": "Crypto ETF Flows"},
    {"ticker": "Cash", "weight": 65.5, "signal": "Reserve", "risk": "Low", "theme": "Liquidity"},
]


def _metric(name: str, value: str, label: str, score: float, trend: str = "up", status: str = "Positive", data_type: str = "Demo Data") -> FundamentalMetric:
    return FundamentalMetric(name, value, label, score, FUNDAMENTAL_WEIGHTS[name], trend, status, data_type=data_type)


def _base_metrics(ticker: str) -> list[FundamentalMetric]:
    profiles = {
        "AMPX": [("+97%", "TTM YoY", 8.5, "up", "Positive"), ("28%", "TTM", 7.0, "up", "Positive"), ("-72%", "Op. Loss YoY", 6.5, "up", "Positive"), ("-$46M", "TTM", 4.0, "down", "Negative"), ("Strong", "Low Debt", 7.5, "up", "Positive"), ("Growing", "Backlog +86% YoY", 7.5, "up", "Positive"), ("Niche Tech", "Silicon Anode IP", 7.0, "flat", "Positive"), ("Good", "Milestones Hit", 7.0, "up", "Positive")],
        "MRVL": [("+6%", "TTM YoY", 6.2, "up", "Neutral"), ("47%", "TTM", 7.6, "flat", "Positive"), ("Improving", "AI mix leverage", 6.8, "up", "Positive"), ("Positive", "TTM FCF", 5.7, "flat", "Neutral"), ("Levered", "Debt from acquisitions", 6.7, "flat", "Neutral"), ("Strong", "Hyperscaler demand", 8.0, "up", "Positive"), ("Custom Silicon", "ASIC and DSP capability", 8.1, "up", "Positive"), ("AI Ramp", "Execution tracking", 7.5, "up", "Positive")],
        "NVDA": [("+78%", "TTM YoY", 9.2, "up", "Positive"), ("73%", "TTM", 9.4, "up", "Positive"), ("Strong", "Operating leverage", 8.8, "up", "Positive"), ("Positive", "FCF generation", 9.0, "up", "Positive"), ("Fortress", "Net cash", 9.1, "up", "Positive"), ("AI Backlog", "Hyperscaler demand", 9.3, "up", "Positive"), ("Dominant", "GPU ecosystem", 9.6, "up", "Positive"), ("Excellent", "Platform execution", 9.0, "up", "Positive")],
        "IONQ": [("+88%", "TTM YoY", 8.2, "up", "Positive"), ("54%", "TTM", 7.0, "flat", "Positive"), ("Early", "Pre-scale losses", 5.3, "flat", "Neutral"), ("Negative", "Cash burn", 4.2, "down", "Negative"), ("Net Cash", "No debt", 8.0, "up", "Positive"), ("Developing", "Govt and enterprise pilots", 6.4, "up", "Neutral"), ("Emerging", "Trapped-ion approach", 7.1, "flat", "Positive"), ("Tracking", "Roadmap execution", 6.3, "flat", "Neutral")],
        "MP": [("+18%", "TTM YoY", 6.4, "up", "Positive"), ("22%", "TTM", 5.8, "down", "Neutral"), ("Cyclical", "Commodity sensitivity", 5.7, "flat", "Neutral"), ("Neutral", "Expansion capex", 4.8, "down", "Negative"), ("Improving", "Liquidity available", 6.9, "up", "Neutral"), ("Strategic", "Defense offtake", 7.0, "up", "Positive"), ("Domestic Asset", "US rare earth exposure", 7.7, "up", "Positive"), ("Processing Ramp", "Execution tracking", 6.4, "flat", "Neutral")],
        "VICR": [("Recovering", "Revenue base reset", 5.8, "flat", "Neutral"), ("46%", "TTM", 6.8, "up", "Positive"), ("Improving", "Margin recovery", 6.1, "up", "Neutral"), ("Positive", "Cash generation", 6.2, "flat", "Positive"), ("Net Cash", "Low debt", 7.2, "up", "Positive"), ("Developing", "Power module demand", 6.0, "flat", "Neutral"), ("Niche Components", "High-performance power", 6.7, "flat", "Positive"), ("Needs Proof", "Scaling consistency", 5.8, "flat", "Neutral")],
        "FBTC": [("Asset flows", "ETF flow sensitivity", 6.5, "up", "Positive"), ("N/A", "Fund structure", 5.5, "flat", "Neutral"), ("N/A", "Fund structure", 5.0, "flat", "Neutral"), ("N/A", "Fund structure", 5.0, "flat", "Neutral"), ("Custody", "Fund structure", 6.0, "flat", "Neutral"), ("ETF Demand", "Institutional allocation", 6.8, "up", "Positive"), ("Distribution", "Issuer scale", 7.0, "up", "Positive"), ("Tracking", "Tracking and liquidity", 6.6, "flat", "Neutral")],
        "CEG": [("+7%", "TTM YoY", 6.5, "up", "Positive"), ("41%", "TTM", 7.9, "up", "Positive"), ("Stable", "Power pricing", 7.4, "flat", "Positive"), ("Positive", "FCF after capex", 7.2, "up", "Positive"), ("Durable", "Utility leverage", 7.1, "flat", "Positive"), ("Power Contracts", "Data-center demand", 8.0, "up", "Positive"), ("Scarce Assets", "Nuclear fleet", 8.2, "up", "Positive"), ("Strong", "Operational execution", 7.7, "up", "Positive")],
    }
    names = ["Revenue Growth", "Gross Margin", "Operating Leverage", "Free Cash Flow", "Balance Sheet", "Customers / Backlog", "Competitive Position", "Execution Quality"]
    fallback = [("N/A", "Live source pending", 5.0, "flat", "Neutral"), ("N/A", "Live source pending", 5.0, "flat", "Neutral"), ("N/A", "Operating trend pending", 5.0, "flat", "Neutral"), ("N/A", "FCF pending", 5.0, "flat", "Neutral"), ("N/A", "Balance sheet pending", 5.0, "flat", "Neutral"), ("Developing", "Customer evidence pending", 5.0, "flat", "Neutral"), ("Unscored", "Competitive review pending", 5.0, "flat", "Neutral"), ("Tracking", "Milestones pending", 5.0, "flat", "Neutral")]
    return [_metric(name, *values) for name, values in zip(names, profiles.get(ticker, fallback))]


def _scenarios(company: Company) -> list[ValuationScenario]:
    return get_valuation_model(company).scenarios


def _market_implied(company: Company, base_revenue: float, base_multiple: float) -> MarketImpliedAssumptions:
    values_by_ticker = {
        "AMPX": (410_000_000, 6.5, 34, 18, base_revenue, base_multiple, 35, 17),
        "MRVL": (9_800_000_000, 8.2, 49, 9, base_revenue, base_multiple, 50, 10),
        "NVDA": (360_000_000_000, 14.0, 72, 19, base_revenue, base_multiple, 73, 20),
        "IONQ": (780_000_000, 10.5, 55, 46, base_revenue, base_multiple, 56, 42),
        "MP": (1_280_000_000, 6.0, 25, 15, base_revenue, base_multiple, 28, 17),
        "FBTC": (68_000_000_000, 1.0, 0, 0, base_revenue, base_multiple, 0, 0),
        "CEG": (42_000_000_000, 3.4, 42, 6, base_revenue, base_multiple, 43, 7),
    }
    values = values_by_ticker.get(
        company.ticker,
        (
            max(company.revenue_ttm or base_revenue, base_revenue),
            base_multiple,
            company.gross_margin or 0,
            0,
            base_revenue,
            base_multiple,
            company.gross_margin or 0,
            0,
        ),
    )
    assumptions = MarketImpliedAssumptions(*values, conclusion="", tone="warn", status="Derived Output")
    return with_market_implied_conclusion(assumptions)


def _must_be_true(company: Company, base: ValuationScenario) -> list[WhatMustBeTrueItem]:
    if company.ticker == "AMPX":
        return [
            WhatMustBeTrueItem("Revenue grows from $82M to $260M by 2028", "Tracking", "Medium", "Revenue Growth", "Base-case revenue path."),
            WhatMustBeTrueItem("Gross margin expands above 35%", "Needs Proof", "Medium", "Gross Margin", "Base-case margin path still needs evidence."),
            WhatMustBeTrueItem("Market assigns ~7x EV/Sales", "At Risk", "Medium", "Multiple Expansion", "Current price already discounts much of the base case."),
            WhatMustBeTrueItem("Dilution remains below 15%", "Needs Monitoring", "Medium", "Dilution Risk", "Per-share value depends on controlled dilution."),
            WhatMustBeTrueItem("Customer adoption accelerates", "Tracking", "Medium", "Customer Demand", "Indirect catalysts need to convert into demand."),
        ]
    metric_value = base.valuation_metric_display or format_financial_value(base.valuation_metric_value, "dollars")
    multiple = f"{base.valuation_multiple:.1f}x" if base.valuation_multiple is not None else "the selected driver"
    if base.valuation_method == "P/E":
        metric_row = (f"EPS model reaches {metric_value} by {base.year}", "Tracking", "Medium", "Earnings Growth", "Based on base-case earnings model.")
    elif base.valuation_method == "EV/EBITDA":
        metric_row = (f"EBITDA model reaches {metric_value} by {base.year}", "Tracking", "Medium", "Earnings Growth", "Based on base-case EBITDA model.")
    elif base.valuation_method == "Asset Price Scenario":
        metric_row = (f"Asset price scenario reaches {metric_value} by {base.year}", "Tracking", "Medium", "Asset Price", "Based on base-case asset price scenario.")
    else:
        metric_row = (f"Revenue model reaches {metric_value} by {base.year}", "Tracking", "Medium", "Revenue Growth", "Based on base-case revenue model.")
    multiple_label = base.valuation_multiple_label if base.valuation_multiple is not None else "NAV/share scenario"
    common = [
        metric_row,
        (f"Market sustains {multiple} {multiple_label}", "Tracking", "Medium", "Valuation Multiple", "Derived from base-case valuation framework."),
        ("Balance sheet risk does not force unfavorable dilution", "Tracking", "Medium", "Dilution Risk", "Based on cash, debt, and cash burn assumptions."),
        ("High-confidence read-through stays net positive", "Tracking", "Medium", "Catalyst / Momentum", "Based on theme exposure map."),
    ]
    ticker_specific = {
        "AMPX": [("Backlog converts into production revenue", "Needs Monitoring", "Medium", "Customer Demand", "Backlog growth is positive, but manufacturing scale remains the proof point."), ("Gross margin expands above 35%", "Tracking", "Medium", "Gross Margin", "Based on base-case operating model.")],
        "IONQ": [("Enterprise pilots convert into commercial workloads", "Needs Monitoring", "Low", "Revenue Growth", "Pilot adoption is still early."), ("Rates stop pressuring speculative duration", "At Risk", "Medium", "Multiple Compression", "Macro read-through remains negative.")],
        "MRVL": [("AI custom silicon revenue offsets non-AI softness", "Tracking", "High", "Revenue Growth", "Hyperscaler capex read-through is positive."), ("Optical networking spend remains elevated", "Tracking", "Medium", "Revenue Growth", "Networking theme remains supportive.")],
        "MP": [("Rare earth pricing stabilizes", "Needs Monitoring", "Medium", "Gross Margin", "Commodity price weakness remains a risk."), ("Reshoring support lowers funding risk", "Tracking", "Medium", "Balance Sheet Risk", "Policy backdrop remains supportive.")],
        "FBTC": [("ETF flows remain positive", "Tracking", "High", "Asset Price", "Recent ETF flow read-through is positive."), ("Real yields do not keep rising", "Needs Monitoring", "Medium", "Risk Premium", "Liquidity read-through is mixed.")],
        "NVDA": [("AI compute demand remains supply constrained", "Tracking", "High", "Revenue Growth", "AI compute read-through remains strong."), ("Gross margin holds near platform peak", "Tracking", "Medium", "Gross Margin", "GPU supply and mix remain supportive.")],
        "CEG": [("Data-center power demand converts into contracts", "Tracking", "High", "Revenue Growth", "Power demand read-through is positive."), ("Grid bottlenecks do not delay load growth", "Needs Monitoring", "Medium", "Execution Risk", "Grid demand read-through flags timing risk.")],
    }
    return [WhatMustBeTrueItem(*row) for row in ticker_specific.get(company.ticker, []) + common]


def _bridge(company: Company, base_price: float) -> list[FutureValueBridgeItem]:
    if company.ticker == "AMPX":
        return [
            FutureValueBridgeItem("Revenue Growth Impact", 7.50, "positive", "Revenue grows toward the 2028 base case."),
            FutureValueBridgeItem("Margin Expansion Impact", 3.25, "positive", "Gross margin improves with scale and mix."),
            FutureValueBridgeItem("Multiple Expansion Impact", 4.00, "positive", "Market assigns a premium EV/Sales framework."),
            FutureValueBridgeItem("Dilution Impact", 1.75, "negative", "Additional shares reduce per-share value."),
            FutureValueBridgeItem("Execution Risk Discount", 2.00, "negative", "Manufacturing and qualification risk remain material."),
        ]
    current = company.current_price
    spread = base_price - current
    if spread >= 0:
        positives = [spread * 0.70, spread * 0.24, spread * 0.20]
        negatives = [spread * 0.06, spread * 0.05, spread * 0.03]
        multiple_label = "Multiple Expansion Impact"
        direction = "positive"
    else:
        positives = [abs(spread) * 0.10, abs(spread) * 0.05, 0.0]
        negatives = [abs(spread) * 0.38, abs(spread) * 0.42, abs(spread) * 0.35]
        multiple_label = "Multiple Compression Impact"
        direction = "negative"
    rows = [
        FutureValueBridgeItem("Revenue Growth Impact", max(0.35, positives[0]), "positive", "Revenue contribution implied by the base-case model."),
        FutureValueBridgeItem("Margin Expansion Impact", max(0.20, positives[1]), "positive", "Operating leverage and mix improvement in the base case."),
        FutureValueBridgeItem(multiple_label, max(0.15, positives[2] if direction == "positive" else negatives[0]), direction, "Change in market valuation multiple versus today."),
        FutureValueBridgeItem("Dilution Impact", max(0.10, negatives[0] if direction == "positive" else negatives[1]), "negative", "Per-share value lost to expected dilution or fund share growth."),
        FutureValueBridgeItem("Execution Risk Discount", max(0.10, negatives[1] if direction == "positive" else negatives[2]), "negative", "Discount for timing, delivery, and operational uncertainty."),
    ]
    return rows


def _risks(ticker: str) -> list[RiskItem]:
    specific = {
        "AMPX": [
            ("Scaling Risk", "Silicon-anode scaling must prove commercial reliability.", "High", "Could reduce revenue assumptions and valuation multiple.", "Customer validation and backlog conversion.", "Active watch"),
            ("Customer Concentration Risk", "Top customers still drive a large share of revenue.", "High", "Raises discount rate and lowers multiple.", "Broader customer base and diversified backlog.", "Monitoring"),
            ("Dilution Risk", "Additional funding could reduce future per-share value.", "Medium", "Reduces future per-share value.", "Improving cash flow and stronger balance sheet.", "Monitoring"),
            ("Execution Risk", "Manufacturing ramp and quality", "Medium", "Delays revenue realization.", "Milestone tracking and quality data.", "Monitoring"),
            ("Competition Risk", "Large battery players entering space", "Medium", "Can cap margins and valuation multiple.", "IP differentiation and niche qualification.", "Monitoring"),
        ],
        "IONQ": [("Commercialization Risk", "Quantum revenue may take longer to materialize.", "High", "Lowers future revenue and multiple.", "Pilot conversion and government demand.", "Active watch"), ("Duration Risk", "Cash flows are far in the future.", "High", "Higher rates compress valuation.", "More near-term customer traction.", "Elevated"), ("Technical Roadmap Risk", "Milestones may not translate to commercial value.", "Medium", "Reduces confidence and multiple.", "Independent benchmarks and customer wins.", "Monitoring")],
        "MRVL": [("Customer Concentration", "Large cloud customers can shift roadmaps.", "Medium", "Creates revenue volatility.", "Multiple ASIC programs.", "Monitoring"), ("Non-AI Cycle Risk", "Legacy end markets remain soft.", "Medium", "Offsets AI growth.", "Mix shift toward data center.", "Monitoring"), ("Execution Risk", "AI ramp timing may slip.", "Medium", "Delays revenue recognition.", "Design-win tracking.", "Monitoring")],
        "MP": [("Commodity Price Risk", "Rare earth prices can remain weak.", "High", "Pressures gross margin.", "Downstream processing and offtake contracts.", "Active watch"), ("Ramp Risk", "Processing expansion may take longer than planned.", "Medium", "Delays revenue realization.", "Milestone tracking.", "Monitoring"), ("Policy Risk", "Supportive policy can change.", "Medium", "Reduces strategic premium.", "Diversified commercial demand.", "Monitoring")],
        "VICR": [("Revenue Recovery Risk", "Power component demand may recover more slowly than modeled.", "Medium", "Lowers revenue assumptions and valuation support.", "Order growth and backlog conversion.", "Monitoring"), ("Margin Normalization Risk", "Gross margin improvement may lag volume recovery.", "Medium", "Reduces future earnings confidence.", "Sustained utilization and mix improvement.", "Monitoring"), ("Customer Timing Risk", "Industrial and data-center power programs can shift timing.", "Medium", "Creates revenue volatility.", "Broader design-win conversion.", "Monitoring")],
        "FBTC": [("Bitcoin Drawdown Risk", "ETF value remains tied to Bitcoin volatility.", "High", "Directly lowers NAV.", "Sizing discipline.", "Elevated"), ("Liquidity Risk", "ETF flows can reverse quickly.", "Medium", "Raises risk premium.", "Track weekly flows.", "Monitoring"), ("Regulatory Risk", "Custody and market rules can change.", "Medium", "Limits institutional adoption.", "Regulatory clarity.", "Monitoring")],
        "NVDA": [("AI Demand Normalization", "Customers may digest capacity after a capex wave.", "Medium", "Compresses revenue growth and multiple.", "Inference demand and platform breadth.", "Monitoring"), ("Gross Margin Peak Risk", "Competition or mix can pressure margins.", "Medium", "Lowers earnings power.", "Software and networking attach.", "Monitoring"), ("Export Control Risk", "Restrictions can limit addressable markets.", "Medium", "Reduces revenue assumptions.", "Compliant product roadmap.", "Monitoring")],
        "CEG": [("Regulatory Risk", "Power pricing and nuclear policy can change.", "Medium", "Reduces multiple and cash flow confidence.", "Long-term contracts.", "Monitoring"), ("Grid Execution Risk", "Interconnection bottlenecks can delay load growth.", "Medium", "Pushes demand realization outward.", "Contract discipline and grid investment.", "Monitoring"), ("Commodity / Fuel Risk", "Fuel and power market volatility can affect margins.", "Low", "Adds earnings volatility.", "Hedging and diversified fleet.", "Contained")],
    }
    fallback = [
        ("Data Quality Risk", "Some live financial fields may be incomplete or provider-dependent.", "Medium", "Can reduce confidence in scoring and valuation.", "Verify against filings and company releases.", "Monitoring"),
        ("Valuation Risk", "Current market expectations may not match the model assumptions.", "Medium", "Can compress expected return.", "Track revenue, margin, and multiple changes.", "Monitoring"),
        ("Execution Risk", "Company-specific milestones need deeper diligence.", "Medium", "Can delay thesis realization.", "Add ticker-specific milestones.", "Monitoring"),
    ]
    return [RiskItem(idx, *row) for idx, row in enumerate(specific.get(ticker, fallback), start=1)]


def _thesis_updates(company: Company, readthrough_count: int) -> list[ThesisUpdate]:
    latest = {
        "AMPX": [
            ("Defense drone procurement funding increased", "Macro / Indirect Catalyst", "Indirect", "Positive", "Customer Demand", "Revenue Growth", "Revenue confidence +0.2", "Supports demand for lightweight, high-energy-density batteries.", "Base revenue +0%", "Base revenue +1%"),
            ("AI infrastructure capex guidance raised by hyperscalers", "Indirect Catalyst", "Indirect", "Positive", "Adjacent Demand", "Revenue Growth", "Catalyst support +0.1", "Long-term boost to data-center power and networking demand.", "Catalyst 6.8", "Catalyst 7.0"),
            ("10Y treasury yield moves higher to 4.48%", "Macro", "Indirect", "Negative", "Valuation Sensitivity", "Multiple Compression", "Risk discount +0.2", "Higher discount rates pressure long-duration growth stocks.", "Discount rate Medium", "Discount rate High"),
        ],
        "MRVL": [("Hyperscalers lift AI capex guidance", "Indirect Catalyst", "Indirect", "Positive", "Customer Demand", "Revenue Growth", "Catalyst score +0.4", "AI capex supports custom silicon and optical networking demand.", "Catalyst 7.1", "Catalyst 7.5"), ("Non-AI chip inventory digestion continues", "Sector", "Indirect", "Negative", "Cyclical Demand", "Gross Margin", "Margin confidence -0.1", "Legacy end-market softness can offset AI strength.", "GM case 51%", "GM case 50%")],
        "IONQ": [("Quantum R&D awards expand pilot funding", "Policy / Indirect Catalyst", "Indirect", "Positive", "Customer Demand", "Revenue Growth", "Catalyst score +0.2", "Government funding validates early-stage quantum demand.", "Revenue confidence Low", "Revenue confidence Medium"), ("Treasury yields move higher", "Macro", "Indirect", "Negative", "Valuation Sensitivity", "Multiple Compression", "Risk discount +0.2; catalyst score -0.4", "Higher rates reduce present value of long-duration growth companies.", "Multiple 9.5x", "Multiple 9.0x")],
        "MP": [("Rare earth export controls tighten", "Policy / Indirect Catalyst", "Indirect", "Positive", "Strategic Value", "Multiple Expansion", "Multiple support +0.3", "Supply chain stress increases strategic value of domestic assets.", "Base multiple 6.2x", "Base multiple 6.5x"), ("Rare earth prices remain soft", "Commodity", "Indirect", "Negative", "Margin Trend", "Gross Margin", "Margin score -0.2", "Weak spot pricing can pressure near-term earnings.", "GM case 30%", "GM case 28%")],
        "VICR": [("Power module demand shows early recovery signs", "Company / Sector", "Indirect", "Positive", "Customer Demand", "Revenue Growth", "Revenue confidence +0.2", "Improving power electronics demand supports the revenue recovery case.", "Revenue confidence Low", "Revenue confidence Medium"), ("Margin recovery remains the proof point", "Company / Operating", "Direct", "Neutral", "Profitability", "Gross Margin", "Keep risk adjustment unchanged", "Upside requires utilization and mix to normalize, not just revenue growth.", "GM case 45%", "GM case 46%")],
        "FBTC": [("Spot Bitcoin ETF inflows continue", "Market Flow", "Indirect", "Positive", "Asset Demand", "Asset Price", "Catalyst score +0.5", "Institutional demand supports Bitcoin-linked fund flows.", "Flow trend Neutral", "Flow trend Positive"), ("Real yields rise", "Macro", "Indirect", "Negative", "Liquidity Sensitivity", "Risk Premium", "Risk score -0.2", "Higher real yields can reduce appetite for volatile crypto exposure.", "Risk premium Medium", "Risk premium High")],
        "NVDA": [("AI compute clusters keep expanding", "Sector / Indirect Catalyst", "Indirect", "Positive", "Customer Demand", "Revenue Growth", "Revenue confidence +0.3", "AI workloads support GPU and platform demand.", "Demand High", "Demand Very High"), ("Export-control risk remains active", "Regulatory", "Indirect", "Negative", "Market Access", "Revenue Growth", "Risk score -0.1", "Restrictions can limit addressable markets.", "Risk Medium", "Risk Medium")],
        "CEG": [("Data-center power contracts lengthen", "Indirect Catalyst", "Indirect", "Positive", "Customer Demand", "Revenue Growth", "Catalyst score +0.4", "Long-duration contracts improve revenue visibility.", "Contract visibility Medium", "Contract visibility High"), ("Grid queues remain a bottleneck", "Infrastructure", "Indirect", "Negative", "Execution Timing", "Execution Risk", "Timing confidence -0.2", "Interconnection delays can slow customer additions.", "Execution risk Medium", "Execution risk Medium")],
    }
    fallback = [
        ("Live quote and financial source connected", "Data Source", "Direct", "Neutral", "Data Quality", "Model Confidence", "Live data loaded", "Ticker search now updates the dashboard from the live adapter when available.", "Demo only", "Live adapter"),
        ("Ticker-specific thesis still needs analyst review", "Research Workflow", "Direct", "Neutral", "Thesis Detail", "Risk Adjustment", "Keep conviction medium", "The generic model should be treated as a starting point until a ticker-specific thesis is added.", "Unscored", "Initial score"),
    ]
    dates = ["2026-06-01", "2026-06-01", "2026-05-18"]
    return [ThesisUpdate(date=dates[idx] if idx < len(dates) else "2026-06-01", title=row[0], type=row[1], directness=row[2], impact=row[3], affected_thesis_lever=row[4], affected_valuation_lever=row[5], dashboard_adjustment=row[6], explanation=row[7], before_value=row[8], after_value=row[9]) for idx, row in enumerate(latest.get(company.ticker, fallback))]


def _decision_drivers(company: Company, updates: list[ThesisUpdate]) -> tuple[list[str], list[str]]:
    if company.ticker == "AMPX":
        return (
            [
                "Supports demand for lightweight, high-energy-density batteries.",
                "Defense drone adoption increases the value of battery endurance.",
                "Revenue path to $260M depends on customer conversion.",
            ],
            [
                "Higher rates pressure speculative growth multiples.",
                "Silicon-anode scaling must prove commercial reliability.",
                "Top customers still drive a large share of revenue.",
            ],
        )
    positive = [item.explanation for item in updates if item.impact == "Positive"]
    negative = [item.explanation for item in updates if item.impact == "Negative"]
    return (
        positive[:3] or ["Positive evidence needs to convert into measurable revenue and margin progress."],
        negative[:3] or ["Risk evidence is limited, but model assumptions still need validation."],
    )


def _key_levers(company: Company, must_be_true: list[WhatMustBeTrueItem], bridge: list[FutureValueBridgeItem]) -> list[str]:
    if company.ticker == "AMPX":
        return [
            "Revenue Growth",
            "Gross Margin",
            "Valuation Multiple",
            "Dilution / Cash Runway",
            "Customer Conversion",
        ]
    levers = []
    for item in must_be_true:
        if item.valuation_lever not in levers:
            levers.append(item.valuation_lever)
    for item in bridge:
        if item.label not in levers:
            levers.append(item.label)
    return levers[:5]


def _ampx_reference_readthrough() -> list[MarketReadThroughItem]:
    rows = [
        ("2025-05-20", "U.S. defense agencies increase funding for small autonomous drones", "Military Drones", ["AMPX", "AVAV", "KTOS", "RCAT"], "Positive", 2.1, "Medium", "Military drones need lightweight, high-density batteries; endurance is a bottleneck.", "Supports AMPX demand because drone endurance and battery weight are bottlenecks.", "Revenue Growth", "Strengthens demand thesis"),
        ("2025-05-20", "Hyperscalers raise AI infrastructure capex outlook", "AI Data Centers", ["MRVL", "NVDA", "DELL", "VRT", "CEG"], "Positive", 2.4, "High", "AI capex lifts adjacent infrastructure demand and risk appetite for enabling technologies.", "Long-term boost to data-center power and networking demand.", "Revenue Growth / Multiple Expansion", "Strengthens adjacent catalyst backdrop"),
        ("2025-05-19", "China tightens rare earth export controls", "Critical Minerals", ["MP", "REMX", "LAC", "Defense Supply"], "Positive", 1.8, "Medium", "Supply-chain stress raises strategic value for domestic critical inputs.", "Defense supply chains may favor domestic and allied enabling technologies.", "Multiple Expansion", "Strengthens strategic supply-chain thesis"),
        ("2025-05-19", "Bitcoin ETF inflows continue", "Crypto & Digital Assets", ["FBTC", "COIN", "MSTR", "Miners"], "Positive", 1.6, "Medium", "ETF inflows support speculative liquidity and appetite for high-upside assets.", "Improved risk appetite can support growth and speculative technology multiples.", "Risk Appetite", "Strengthens market-risk backdrop"),
        ("2025-05-18", "10Y yield moves higher on sticky inflation", "Rates / Macro", ["IONQ", "Growth", "Long Duration"], "Negative", -1.5, "Medium", "Higher rates reduce the present value of distant cash flows.", "Higher discount rates pressure long-duration growth stocks.", "Multiple Compression", "Weakens valuation support"),
    ]
    return [MarketReadThroughItem(*row) for row in rows]


def _sensitivity(company: Company, base: ValuationScenario) -> SensitivityTable:
    metric_value = base.valuation_metric_value or base.revenue
    if base.valuation_method == "P/E":
        revenues = [metric_value * factor for factor in (0.75, 0.9, 1.0, 1.1, 1.25)]
        multiples = [max(1.0, (base.valuation_multiple or base.ev_sales_multiple) + offset) for offset in (-6, -3, 0, 3, 6)]
        values = {}
        for multiple in multiples:
            for metric in revenues:
                values[(metric, multiple)] = round(metric * multiple, 2)
        return SensitivityTable(revenues, multiples, values, (metric_value, base.valuation_multiple or base.ev_sales_multiple), "Highlighted cell is the base-case EPS x P/E assumption.")
    if base.valuation_method == "Asset Price Scenario":
        revenues = [metric_value * factor for factor in (0.65, 0.85, 1.0, 1.2, 1.5)]
        multiples = [0.90, 1.00, 1.10]
        values = {}
        for nav_factor in multiples:
            for asset_price in revenues:
                values[(asset_price, nav_factor)] = round(company.current_price * (asset_price / metric_value) * nav_factor, 2) if metric_value else 0.0
        return SensitivityTable(revenues, multiples, values, (metric_value, 1.00), "Highlighted cell is the base-case asset price and NAV/share sensitivity.")
    revenues = [metric_value * factor for factor in (0.6, 0.8, 1.0, 1.2, 1.5)]
    multiples = [max(0.5, (base.valuation_multiple or base.ev_sales_multiple) + offset) for offset in (-3, -1.5, 0, 1.5, 3)]
    values: dict[tuple[float, float], float] = {}
    for multiple in multiples:
        for revenue in revenues:
            values[(revenue, multiple)] = calculate_future_share_price(revenue=revenue, multiple=multiple, net_debt=base.net_debt, diluted_shares_outstanding=base.diluted_shares_outstanding)
    return SensitivityTable(revenues, multiples, values, (metric_value, base.valuation_multiple or base.ev_sales_multiple), "Highlighted cell is the exact base-case valuation assumption. Values are future share price estimates.")


def _events_for_ticker(ticker: str) -> list[dict[str, str]]:
    return [event for event in UPCOMING_EVENTS if event["ticker"] in {ticker, "FOMC"}][:3]


def _thesis_summary(company: Company, items: list, updates: list[ThesisUpdate]) -> ThesisChangeSummary:
    net_score = calculate_net_readthrough_score(items)
    status = "Strengthening" if net_score >= 1.0 else "Weakening" if net_score <= -1.0 else "Stable"
    positive = next((item for item in sorted(items, key=lambda row: row.impact_score, reverse=True) if item.impact_score > 0), None)
    negative = next((item for item in sorted(items, key=lambda row: row.impact_score) if item.impact_score < 0), None)
    latest_driver = updates[0].explanation if updates else "No recent thesis update."
    lever_counts = Counter(item.affected_valuation_lever for item in items)
    most_affected = lever_counts.most_common(1)[0][0] if lever_counts else "N/A"
    return ThesisChangeSummary(
        status=status,
        net_thesis_impact_score=net_score,
        latest_driver=latest_driver,
        positive_read_through=positive.market_update if positive else "No positive read-through currently attached.",
        negative_read_through=negative.market_update if negative else "No negative read-through currently attached.",
        most_affected_valuation_lever=most_affected,
        last_updated=company.last_updated,
    )


def _valuation_score(expected_return: float) -> float:
    if expected_return >= 100:
        return 8.8
    if expected_return >= 50:
        return 8.0
    if expected_return >= 20:
        return 7.0
    if expected_return >= 0:
        return 5.6
    return 3.8


def build_company_analysis_for_company(company: Company) -> CompanyAnalysis:
    metrics = _base_metrics(company.ticker)
    valuation_model = get_valuation_model(company)
    scenarios = valuation_model.scenarios
    expected_value = valuation_model.expected_value or 0.0
    expected_detail = calculate_expected_value_detail(scenarios, company.current_price)
    base = next(item for item in scenarios if item.name == "Base Case")
    readthrough = _ampx_reference_readthrough() if company.ticker == "AMPX" else get_theme_read_through_for_ticker(company.ticker, company.themes, MARKET_UPDATES, THEME_EXPOSURES)
    updates = _thesis_updates(company, len(readthrough))
    thesis_summary = _thesis_summary(company, readthrough, updates)
    must_be_true = _must_be_true(company, base)
    bridge = _bridge(company, base.future_share_price)
    positive_drivers, negative_drivers = _decision_drivers(company, updates)
    key_levers = _key_levers(company, must_be_true, bridge)
    fundamental_score = calculate_fundamental_score(metrics)
    expected_return = calculate_expected_return(expected_value, company.current_price)
    catalyst_score = max(3.0, min(9.0, 5.8 + calculate_net_readthrough_score(readthrough) * 0.7))
    valuation_score = _valuation_score(expected_return)
    risk_level = "High" if company.ticker in {"AMPX", "IONQ", "FBTC"} else "Medium"
    risk_score = 3.2 if risk_level == "High" else 7.0
    total_score = calculate_investment_signal(fundamental_score=fundamental_score, valuation_upside_score=valuation_score, catalyst_momentum_score=catalyst_score, risk_adjustment_score=risk_score)
    signal_label = classify_investment_signal(total_score)
    signal = InvestmentSignal(
        signal=signal_label,
        total_score=total_score,
        conviction="Medium" if risk_level == "High" else "High",
        risk_level=risk_level,
        summary=generate_signal_summary(signal_label, risk_level),
        score_breakdown={"Fundamental Score": (fundamental_score, 0.35), "Valuation / Upside": (valuation_score, 0.30), "Catalyst / Momentum": (catalyst_score, 0.20), "Risk Adjustment": (risk_score, 0.15)},
        upgrade_triggers=["Higher revenue growth", "Improved margin trend", "Lower dilution risk", "Positive high-confidence read-through", "Stronger balance sheet"],
        downgrade_triggers=["Revenue miss", "Margin deterioration", "Higher cash burn", "Negative read-through", "Multiple compression"],
    )
    return CompanyAnalysis(
        company=company,
        fundamental_metrics=metrics,
        valuation_scenarios=scenarios,
        expected_value=expected_value,
        expected_value_detail=expected_detail,
        thesis_summary=thesis_summary,
        what_must_be_true=must_be_true,
        future_value_bridge=bridge,
        market_implied_assumptions=_market_implied(company, base.revenue, base.ev_sales_multiple),
        market_read_through=readthrough,
        thesis_updates=updates,
        risks=_risks(company.ticker),
        sensitivity_table=_sensitivity(company, base),
        investment_signal=signal,
        positive_drivers=positive_drivers,
        negative_drivers=negative_drivers,
        key_levers=key_levers,
        next_events=_events_for_ticker(company.ticker),
        valuation_model=valuation_model,
    )


def build_company_analysis(ticker: str) -> CompanyAnalysis:
    company = COMPANIES.get(ticker.upper())
    if company is None:
        raise KeyError(f"Unknown demo ticker: {ticker}")
    return build_company_analysis_for_company(company)


ANALYSES = {ticker: build_company_analysis(ticker) for ticker in COMPANIES}


def all_watchlist_rows() -> list[dict[str, object]]:
    rows = []
    for ticker, analysis in ANALYSES.items():
        company = analysis.company
        rows.append({"Ticker": ticker, "Company": company.company_name, "Price": company.current_price, "Daily Change": company.daily_change, "Fundamental Score": calculate_fundamental_score(analysis.fundamental_metrics), "Expected Return": calculate_expected_return(analysis.expected_value, company.current_price), "Net Thesis Impact": analysis.thesis_summary.net_thesis_impact_score, "Latest Thesis Impact": analysis.thesis_updates[0].impact if analysis.thesis_updates else "Neutral", "Investment Signal": analysis.investment_signal.signal, "Risk Level": analysis.investment_signal.risk_level, "Theme": company.themes[0]})
    return rows


def screener_rows() -> list[dict[str, object]]:
    rows = []
    for ticker, analysis in ANALYSES.items():
        rows.append({"Ticker": ticker, "Company": analysis.company.company_name, "Sector": analysis.company.sector, "Fundamental Score": calculate_fundamental_score(analysis.fundamental_metrics), "Expected Return": calculate_expected_return(analysis.expected_value, analysis.company.current_price), "Read-Through Score": calculate_net_readthrough_score(analysis.market_read_through), "Risk Level": analysis.investment_signal.risk_level, "Investment Signal": analysis.investment_signal.signal, "Theme": analysis.company.themes[0], "Market Cap": analysis.company.market_cap, "Revenue Growth": analysis.fundamental_metrics[0].value, "Gross Margin": analysis.fundamental_metrics[1].value})
    return rows


def business_quality_label(ticker: str) -> str:
    analysis = ANALYSES[ticker]
    return classify_business_quality(calculate_fundamental_score(analysis.fundamental_metrics))


def bridge_value(ticker: str) -> float:
    analysis = ANALYSES[ticker]
    start_price = 12.00 if ticker == "AMPX" else analysis.company.current_price
    return calculate_future_value_bridge(start_price, analysis.future_value_bridge)
