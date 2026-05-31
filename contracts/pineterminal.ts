export type Impact = "Strong Positive" | "Positive" | "Neutral" | "Negative" | "Strong Negative";
export type Confidence = "Low" | "Medium" | "High";
export type DataType = "Actual" | "Estimated" | "Model Assumption" | "Derived Output" | "Demo Data" | "Model-Derived";
export type Signal = "Strong Buy" | "Buy" | "Speculative Buy" | "Hold" | "Avoid" | "Sell";

export interface CompanyProfile {
  ticker: string;
  companyName: string;
  sector: string;
  industry: string;
  themes: string[];
  currentPrice: number | null;
  dayChangeDollar: number | null;
  dayChangePercent: number | null;
  preMarketChangePercent: number | null;
  afterHoursChangePercent: number | null;
  marketCap: number | null;
  enterpriseValue: number | null;
  week52Low: number | null;
  week52High: number | null;
  week52CurrentPosition: number;
  fundamentalScore: number;
  fundamentalLabel: string;
  expected36MReturn: number;
  expectedReturnLabel: string;
  investmentSignal: Signal;
  confidence: string;
  riskLevel: string;
  marketStatus: "Open" | "Closed";
  lastUpdated: string;
}

export interface FundamentalMetric {
  name: string;
  value: string;
  unit: string;
  context: string;
  score: number;
  weight: number;
  status: "Positive" | "Neutral" | "Negative";
  trend: "up" | "flat" | "down";
  dataType: DataType;
}

export interface ValuationScenario {
  name: "Bear Case" | "Base Case" | "Bull Case";
  year: number;
  revenue: number;
  evSalesMultiple: number;
  futureEnterpriseValue: number;
  netDebt: number;
  dilutedSharesOutstanding: number;
  futureSharePrice: number;
  impliedReturn: number;
  probability: number;
  keyAssumption: string;
  dataType: DataType;
}

export interface ExpectedValue {
  expectedValuePrice: number;
  currentPrice: number;
  expectedReturn: number;
  scenarioContributions: Record<string, number>;
}

export interface WhatMustBeTrueItem {
  description: string;
  status: "Met" | "Tracking" | "Needs Monitoring" | "At Risk" | "Not Met";
  confidence: Confidence;
  valuationLever: string;
  evidence: string;
}

export interface FutureValueBridgeItem {
  label: string;
  impact: number;
  direction: "positive" | "negative";
  explanation: string;
}

export interface MarketImpliedAssumptions {
  impliedRevenue: number;
  impliedEvSales: number;
  impliedGrossMargin: number;
  impliedRevenueCagr: number;
  baseRevenue: number;
  baseEvSales: number;
  baseGrossMargin: number;
  baseRevenueCagr: number;
  conclusion: string;
  status: DataType;
}

export interface ThemeExposure {
  theme: string;
  impactedTickers: string[];
  transmissionPath: string;
  defaultImpact: "Positive" | "Negative" | "Neutral";
  valuationLevers: string[];
  timeHorizon: string;
}

export interface MarketReadThroughItem {
  date: string;
  marketUpdate: string;
  theme: string;
  impactedTickers: string[];
  impact: Impact;
  impactScore: number;
  confidence: Confidence;
  transmissionPath: string;
  whyItMatters: string;
  affectedValuationLever: string;
}

export interface ThesisUpdate {
  date: string;
  title: string;
  type: string;
  directness: "Direct" | "Indirect";
  impact: Impact;
  thesisLever: string;
  valuationLever: string;
  dashboardAdjustment: string;
  explanation: string;
  beforeValue: string;
  afterValue: string;
}

export interface RiskItem {
  rank: number;
  riskName: string;
  severity: "Low" | "Medium" | "High";
  description: string;
  valuationImpact: string;
  mitigant: string;
  currentStatus: string;
}

export interface InvestmentSignal {
  signal: Signal;
  totalScore: number;
  conviction: Confidence;
  riskLevel: "Low" | "Medium" | "High";
  summary: string;
  scoreBreakdown: Record<string, { score: number; weight: number }>;
  upgradeTriggers: string[];
  downgradeTriggers: string[];
}

export interface CompanyAnalysis {
  company: CompanyProfile;
  fundamentalMetrics: FundamentalMetric[];
  valuationScenarios: ValuationScenario[];
  expectedValue: ExpectedValue;
  whatMustBeTrue: WhatMustBeTrueItem[];
  futureValueBridge: FutureValueBridgeItem[];
  marketImpliedAssumptions: MarketImpliedAssumptions;
  marketReadThrough: MarketReadThroughItem[];
  thesisUpdates: ThesisUpdate[];
  risks: RiskItem[];
  investmentSignal: InvestmentSignal;
}

export function calculateFundamentalScore(metrics: FundamentalMetric[]): number {
  const result = metrics.reduce((acc, metric) => ({
    score: acc.score + metric.score * metric.weight,
    weight: acc.weight + metric.weight,
  }), { score: 0, weight: 0 });
  return result.weight === 0 ? 0 : Number((result.score / result.weight).toFixed(1));
}

export function calculateScenarioSharePrice(scenario: ValuationScenario): number {
  const futureEnterpriseValue = scenario.revenue * scenario.evSalesMultiple;
  const futureEquityValue = futureEnterpriseValue - scenario.netDebt;
  return scenario.dilutedSharesOutstanding <= 0 ? 0 : Number((futureEquityValue / scenario.dilutedSharesOutstanding).toFixed(2));
}

export function calculateScenarioReturn(futureSharePrice: number, currentPrice: number): number {
  return currentPrice === 0 ? 0 : Number((((futureSharePrice - currentPrice) / currentPrice) * 100).toFixed(1));
}

export function calculateExpectedValue(scenarios: ValuationScenario[]): number {
  return Number(scenarios.reduce((total, scenario) => total + scenario.futureSharePrice * scenario.probability, 0).toFixed(2));
}

export function calculateExpectedReturn(expectedValuePrice: number, currentPrice: number): number {
  return calculateScenarioReturn(expectedValuePrice, currentPrice);
}

export function calculateFutureValueBridge(currentPrice: number, bridgeItems: FutureValueBridgeItem[]): number {
  return Number(bridgeItems.reduce((value, item) => value + (item.direction === "negative" ? -Math.abs(item.impact) : item.impact), currentPrice).toFixed(2));
}

export function compareMarketImpliedToBaseCase(model: MarketImpliedAssumptions): { conclusion: string; status: "good" | "warn" | "bad" } {
  const gap = model.baseRevenue === 0 ? 0 : (model.impliedRevenue - model.baseRevenue) / model.baseRevenue;
  if (gap > 0.2) return { conclusion: "Market expects more growth than base case. Limited margin for error.", status: "bad" };
  if (gap < -0.2) return { conclusion: "Base case exceeds market expectations. Potential valuation gap.", status: "good" };
  return { conclusion: "Market price broadly aligns with base case.", status: "warn" };
}

export function calculateNetReadThroughScore(items: MarketReadThroughItem[]): number {
  const confidenceWeight = (confidence: Confidence) => confidence === "High" ? 1 : confidence === "Medium" ? 0.75 : 0.55;
  const result = items.reduce((acc, item) => {
    const weight = confidenceWeight(item.confidence);
    return { score: acc.score + item.impactScore * weight, weight: acc.weight + weight };
  }, { score: 0, weight: 0 });
  return result.weight === 0 ? 0 : Number((result.score / result.weight).toFixed(1));
}

export function classifyImpactScore(score: number): Impact {
  if (score >= 3.5) return "Strong Positive";
  if (score >= 1.0) return "Positive";
  if (score <= -3.5) return "Strong Negative";
  if (score <= -1.0) return "Negative";
  return "Neutral";
}

export function calculateInvestmentSignal(inputs: {
  fundamentalScore: number;
  valuationUpsideScore: number;
  catalystMomentumScore: number;
  riskAdjustmentScore: number;
}): number {
  return Number((inputs.fundamentalScore * 0.35 + inputs.valuationUpsideScore * 0.30 + inputs.catalystMomentumScore * 0.20 + inputs.riskAdjustmentScore * 0.15).toFixed(1));
}

export function classifyInvestmentSignal(score: number): Signal {
  if (score >= 8.5) return "Strong Buy";
  if (score >= 7.0) return "Buy";
  if (score >= 6.0) return "Speculative Buy";
  if (score >= 4.5) return "Hold";
  if (score >= 3.0) return "Avoid";
  return "Sell";
}

export function generateSignalSummary(signal: Signal): string {
  const summaries: Record<Signal, string> = {
    "Strong Buy": "Strong fundamentals, attractive upside, and supportive catalysts outweigh risks.",
    "Buy": "Positive risk/reward with solid fundamentals and meaningful upside.",
    "Speculative Buy": "High upside, high risk. Thesis is promising but execution risk remains material.",
    "Hold": "Balanced setup. Upside and risk are roughly matched.",
    "Avoid": "Risk/reward is unattractive. Upside does not adequately compensate for fundamental or valuation risk.",
    "Sell": "Thesis appears impaired or valuation/risk profile is unfavorable.",
  };
  return summaries[signal];
}
