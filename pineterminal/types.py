from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Company:
    ticker: str
    company_name: str
    sector: str
    industry: str
    themes: list[str]
    current_price: float
    daily_change: float
    market_cap: float
    enterprise_value: float
    week52_low: float
    week52_high: float
    currency: str = "USD"
    pre_market_change_percent: float = 0.0
    after_hours_change_percent: float = 0.0
    market_status: str = "Closed"
    last_updated: str = "2026-05-31 13:45 ET"
    data_mode: str = "Demo"
    data_source: str = "Demo Data"
    revenue_ttm: float | None = None
    gross_margin: float | None = None
    cash: float | None = None
    debt: float | None = None
    day_change_dollar: float | None = None
    shares_outstanding: float | None = None
    cash_burn_ttm: float | None = None


@dataclass(frozen=True)
class CompanyProfile:
    ticker: str
    company_name: str
    sector: str
    industry: str
    themes: list[str]
    current_price: float | None
    day_change_dollar: float | None
    day_change_percent: float | None
    market_cap: float | None
    enterprise_value: float | None
    week52_low: float | None
    week52_high: float | None
    week52_current_position: float
    fundamental_score: float
    fundamental_label: str
    expected36m_return: float
    expected_return_label: str
    investment_signal: str
    confidence: str
    risk_level: str
    market_status: str
    last_updated: str
    data_mode: str
    data_source: str
    pre_market_change_percent: float | None
    after_hours_change_percent: float | None


@dataclass(frozen=True)
class FundamentalMetric:
    name: str
    value: str
    label: str
    score: float
    weight: float
    trend: str
    status: str
    unit: str = ""
    data_type: str = "Demo Data"


@dataclass(frozen=True)
class ValuationScenario:
    name: str
    year: int
    revenue: float
    ev_sales_multiple: float
    future_enterprise_value: float
    net_debt: float
    diluted_shares_outstanding: float
    future_share_price: float
    implied_return: float
    probability: float
    assumption: str
    data_type: str = "Model Assumption / Derived Output"


@dataclass(frozen=True)
class WhatMustBeTrueItem:
    description: str
    status: str
    confidence: str
    valuation_lever: str
    evidence: str = "Based on demo model assumptions."


@dataclass(frozen=True)
class FutureValueBridgeItem:
    label: str
    value_impact: float
    type: str
    explanation: str = "Model bridge contribution."


@dataclass(frozen=True)
class MarketImpliedAssumptions:
    implied_revenue: float
    implied_ev_sales: float
    implied_gross_margin: float
    implied_revenue_cagr: float
    base_revenue: float
    base_ev_sales: float
    base_gross_margin: float
    base_revenue_cagr: float
    conclusion: str
    tone: str
    status: str = "Derived Output"


@dataclass(frozen=True)
class MarketReadThroughItem:
    date: str
    market_update: str
    theme: str
    impacted_tickers: list[str]
    impact: str
    impact_score: float
    confidence: str
    transmission_path: str
    why_it_matters: str
    affected_valuation_lever: str
    thesis_impact: str = "Thesis impact mapped from theme exposure."


@dataclass(frozen=True)
class ThesisUpdate:
    date: str
    title: str
    type: str
    impact: str
    affected_thesis_lever: str
    affected_valuation_lever: str
    dashboard_adjustment: str
    explanation: str
    directness: str = "Indirect"
    before_value: str = "N/A"
    after_value: str = "N/A"


@dataclass(frozen=True)
class RiskItem:
    rank: int
    risk_name: str
    description: str
    severity: str
    valuation_impact: str
    mitigant: str
    current_status: str = "Monitoring"


@dataclass(frozen=True)
class InvestmentSignal:
    signal: str
    total_score: float
    conviction: str
    risk_level: str
    summary: str
    score_breakdown: dict[str, tuple[float, float]]
    upgrade_triggers: list[str] = field(default_factory=list)
    downgrade_triggers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ThemeExposure:
    theme: str
    impacted_tickers: list[str]
    transmission_path: str
    default_impact: str
    related_valuation_levers: list[str]
    last_update_date: str
    time_horizon: str = "6-36 months"


@dataclass(frozen=True)
class ThesisChangeSummary:
    status: str
    net_thesis_impact_score: float
    latest_driver: str
    positive_read_through: str
    negative_read_through: str
    most_affected_valuation_lever: str
    last_updated: str


@dataclass(frozen=True)
class ExpectedValue:
    expected_value_price: float
    current_price: float
    expected_return: float
    scenario_contributions: dict[str, float]


@dataclass(frozen=True)
class SensitivityTable:
    revenue_columns: list[float]
    multiple_rows: list[float]
    values: dict[tuple[float, float], float]
    highlighted_cell: tuple[float, float]
    note: str


@dataclass(frozen=True)
class CompanyAnalysis:
    company: Company
    fundamental_metrics: list[FundamentalMetric]
    valuation_scenarios: list[ValuationScenario]
    expected_value: float
    expected_value_detail: ExpectedValue
    thesis_summary: ThesisChangeSummary
    what_must_be_true: list[WhatMustBeTrueItem]
    future_value_bridge: list[FutureValueBridgeItem]
    market_implied_assumptions: MarketImpliedAssumptions
    market_read_through: list[MarketReadThroughItem]
    thesis_updates: list[ThesisUpdate]
    risks: list[RiskItem]
    sensitivity_table: SensitivityTable
    investment_signal: InvestmentSignal
    next_events: list[dict[str, str]] = field(default_factory=list)
