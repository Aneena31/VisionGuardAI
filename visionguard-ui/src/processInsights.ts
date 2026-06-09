const DEFAULT_RULE_TOTAL = 11;

const toScore = (value: unknown) => {
  const score = Number(value || 0);
  return Number.isFinite(score) ? score : 0;
};

export const buildProcessInsights = (analysis: any, claim: any): string[] => {
  const apiInsights = analysis?.processInsights;
  if (Array.isArray(apiInsights) && apiInsights.length > 0) {
    return apiInsights.map((item) => String(item)).filter(Boolean).slice(0, 4);
  }

  const rules = analysis?.rulesAnalysis || {};
  const triggeredRules = Array.isArray(rules.triggeredRules) ? rules.triggeredRules : [];
  const failedRules = Number(rules.failedRules ?? triggeredRules.length ?? 0);
  const totalRules = Number(rules.totalRules ?? DEFAULT_RULE_TOTAL);
  const passedRules = Math.max(0, totalRules - failedRules);
  const claimPatternScore = toScore(analysis?.statisticalAnalysis?.claimPatternScore);
  const providerPatternScore = toScore(analysis?.statisticalAnalysis?.providerPatternScore);
  const mlScore = toScore(analysis?.mlAnalysis?.anomalyScore ?? claim?.fraudScore);

  const insights = [
    failedRules > 0
      ? `${failedRules} rule violations found`
      : 'No rule violations',
  ];

  if (claimPatternScore >= 70 && providerPatternScore >= 70) {
    insights.push('Unusual claim and provider billing');
  } else if (claimPatternScore >= 70) {
    insights.push('Unusual claim billing');
  } else if (providerPatternScore >= 70) {
    insights.push('Unusual provider billing');
  } else if (claimPatternScore >= 40 || providerPatternScore >= 40) {
    insights.push('Moderate billing variation');
  } else {
    insights.push('Normal billing patterns');
  }

  if (mlScore >= 75) {
    insights.push('High anomaly concern');
  } else if (mlScore >= 50) {
    insights.push('Moderate anomaly concern');
  } else {
    insights.push(mlScore >= 25 ? 'Low anomaly concern' : 'No anomaly concern');
  }

  return insights.slice(0, 3);
};
