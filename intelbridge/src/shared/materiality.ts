export type MaterialityFactors = {
  confidence: number;
  impact: number;
  novelty: number;
  relevance: number;
  sourceQuality: number;
  urgency: number;
};

export function calculateMateriality(factors: MaterialityFactors) {
  return Object.values(factors)
    .map((factor) => Math.min(1, Math.max(0, factor)))
    .reduce((score, factor) => score * factor, 1);
}
