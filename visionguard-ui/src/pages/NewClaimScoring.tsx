import React, { useState, useEffect, useRef } from 'react';
import { GlassCard } from '../components/ui';
import { motion, AnimatePresence } from 'motion/react';
import { FileText, Loader2, ShieldAlert, Activity, BrainCircuit, Users, Zap, ArrowRight, Mail, CheckCircle } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { api } from '../api';
import { buildProcessInsights } from '../processInsights';

type Step = 'upload' | 'processing' | 'result';

type SampleClaim = {
  id: string;
  filename: string;
  label: string;
  claim: Record<string, any>;
};

type ClaimDraft = {
  procedureCode: string;
  procedureDesc: string;
  allowedAmount: string;
  amtCharged: string;
  units: string;
  memberAge: string;
  memberGender: string;
  memberId: string;
  providerId: string;
  serviceDate: string;
  benefitType: string;
  serviceCategoryName: string;
  benefitCategoryName: string;
};

const claimFields: Array<{ key: keyof ClaimDraft; label: string; type?: string }> = [
  { key: 'procedureCode', label: 'Procedure Code' },
  { key: 'procedureDesc', label: 'Procedure Description' },
  { key: 'allowedAmount', label: 'Allowed Amount', type: 'number' },
  { key: 'amtCharged', label: 'Amount Charged', type: 'number' },
  { key: 'units', label: 'Units', type: 'number' },
  { key: 'memberAge', label: 'Member Age', type: 'number' },
  { key: 'memberGender', label: 'Member Gender' },
  { key: 'memberId', label: 'Member ID' },
  { key: 'providerId', label: 'Provider ID' },
  { key: 'serviceDate', label: 'Service Date', type: 'date' },
  { key: 'benefitType', label: 'Benefit Type' },
  { key: 'serviceCategoryName', label: 'Service Category' },
  { key: 'benefitCategoryName', label: 'Benefit Category' },
];

const toClaimDraft = (claim: Record<string, any>): ClaimDraft => ({
  procedureCode: String(claim.procedureCode ?? ''),
  procedureDesc: String(claim.procedureDesc ?? ''),
  allowedAmount: String(claim.allowedAmount ?? ''),
  amtCharged: String(claim.amtCharged ?? ''),
  units: String(claim.units ?? ''),
  memberAge: String(claim.memberAge ?? ''),
  memberGender: String(claim.memberGender ?? ''),
  memberId: String(claim.memberId ?? ''),
  providerId: String(claim.providerId ?? ''),
  serviceDate: String(claim.serviceDate ?? ''),
  benefitType: String(claim.benefitType ?? ''),
  serviceCategoryName: String(claim.serviceCategoryName ?? ''),
  benefitCategoryName: String(claim.benefitCategoryName ?? ''),
});

const toClaimPayload = (draft: ClaimDraft) => ({
  ...draft,
  allowedAmount: Number(draft.allowedAmount || 0),
  amtCharged: Number(draft.amtCharged || 0),
  units: Number(draft.units || 0),
  memberAge: Number(draft.memberAge || 0),
});

const technicalNarrativePattern = /\b(SD|standard deviation|population mean|z-?score|Isolation Forest|PCA|reconstruction|ML anomaly)\b/i;

const historyConcernLabel = (value: number) => {
  if (value >= 70) return 'Very unusual';
  if (value >= 40) return 'Moderate';
  return 'Typical';
};

const scoreConcernLabel = (value: number) => {
  if (value >= 75) return 'High concern';
  if (value >= 50) return 'Needs review';
  if (value >= 25) return 'Watch';
  return 'Low concern';
};

const businessHistoricalNarrative = (rawNarrative: unknown, claimScore: number) => {
  const narrative = typeof rawNarrative === 'string' ? rawNarrative.trim() : '';
  if (narrative && !technicalNarrativePattern.test(narrative) && !/\bprovider\b/i.test(narrative)) return narrative;
  const claimLabel = historyConcernLabel(claimScore).toLowerCase();
  if (claimScore >= 70) {
    return 'The submitted claim billing profile is unusual compared with prior claims with similar billing characteristics.';
  }
  if (claimScore >= 40) {
    return `The claim is ${claimLabel}; this is worth a business review but is not a high-concern historical mismatch.`;
  }
  return 'The claim looks consistent with expected historical billing patterns.';
};

const businessPatternNarrative = (_rawNarrative: unknown, patternScore: number) => {
  if (patternScore >= 75) {
    return 'High concern; the claim differs from prior behavior and should be reviewed.';
  }
  if (patternScore >= 50) {
    return 'Needs review; the claim has noticeable differences from prior behavior.';
  }
  if (patternScore >= 25) {
    return 'Watch; the claim has some differences from prior behavior.';
  }
  return 'Low concern; the claim is consistent with prior behavior.';
};

const formatCurrency = (value: unknown) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value || 0));

export default function NewClaimScoring() {
  const [step, setStep] = useState<Step>('upload');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [activeAnalysis, setActiveAnalysis] = useState('Preparing claim review...');
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [sampleClaims, setSampleClaims] = useState<SampleClaim[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState('');
  const [sampleLoading, setSampleLoading] = useState(true);
  const [claimDraft, setClaimDraft] = useState<ClaimDraft | null>(null);
  const [assignmentState, setAssignmentState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const scoredClaim = result?.claim;
  const scoredAnalysis = result?.analysis;
  const aiSummary = scoredAnalysis?.aiSummary;
  const triggeredRules = scoredAnalysis?.rulesAnalysis?.triggeredRules || [];
  const failedRuleCount = Number(scoredAnalysis?.rulesAnalysis?.failedRules ?? triggeredRules.length ?? 0);
  const statisticalAnalysis = scoredAnalysis?.statisticalAnalysis || {};
  const mlAnalysis = scoredAnalysis?.mlAnalysis || {};
  const claimPatternScore = Number(statisticalAnalysis?.claimPatternScore ?? 0);
  const claimHistoryLevel = statisticalAnalysis?.claimPatternLevel || historyConcernLabel(claimPatternScore);
  const historicalNarrative = businessHistoricalNarrative(statisticalAnalysis?.narrative, claimPatternScore);
  const isolationForestScore = Number(mlAnalysis?.isolationForestScore || 0);
  const pcaErrorScore = Number(mlAnalysis?.pcaErrorScore || 0);
  const mlAnomalyScore = Number(mlAnalysis?.anomalyScore || 0);
  const patternNarrative = businessPatternNarrative(mlAnalysis?.modelSummary, mlAnomalyScore);
  const clusterAssignment = scoredAnalysis?.clusterAssignment;
  const closestCase = clusterAssignment?.closestCase;
  const fraudScore = Number(scoredClaim?.fraudScore || 0);
  const processInsights = buildProcessInsights(scoredAnalysis, scoredClaim);
  const selectedSample = sampleClaims.find((sample) => sample.id === selectedSampleId);
  const processingSectionRef = useRef<HTMLDivElement | null>(null);
  const resultsSectionRef = useRef<HTMLDivElement | null>(null);

  const beginProcessing = (jobPromise: Promise<any>) => {
    setStep('processing');
    setProcessingProgress(0);
    setActiveAnalysis('Submitting claim for review...');
    setJobId(null);
    setResult(null);
    setUploadError(null);
    setAssignmentState('idle');
    jobPromise
      .then((job) => setJobId(job.jobId))
      .catch((error) => {
        setUploadError(error instanceof Error ? error.message : 'Claim review is unavailable.');
        setActiveAnalysis('Claim review is unavailable.');
        setStep('upload');
      });
  };

  const startSampleProcessing = (draft: ClaimDraft) => {
    beginProcessing(api.createScoringJob({
      sourceType: 'manual',
      claim: toClaimPayload(draft),
    }));
  };

  const selectSample = (sampleId: string) => {
    setSelectedSampleId(sampleId);
    setStep('upload');
    setResult(null);
    setJobId(null);
    setProcessingProgress(0);
    setAssignmentState('idle');
  };

  const analyzeClaim = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!claimDraft) {
      setUploadError('Choose a testcase before analyzing.');
      return;
    }
    startSampleProcessing(claimDraft);
  };

  const sendToInvestigationTeam = async () => {
    if (!jobId || assignmentState === 'sending' || assignmentState === 'sent') return;
    setAssignmentState('sending');
    try {
      await api.assignScoringJob(jobId);
      setAssignmentState('sent');
    } catch {
      setAssignmentState('error');
    }
  };

  useEffect(() => {
    api.getSampleClaims()
      .then((samples: SampleClaim[]) => {
        setSampleClaims(samples);
        setSelectedSampleId(samples[0]?.id || '');
        setClaimDraft(samples[0] ? toClaimDraft(samples[0].claim) : null);
      })
      .catch((error) => {
        setUploadError(error instanceof Error ? error.message : 'Failed to fetch testcases.');
      })
      .finally(() => setSampleLoading(false));
  }, []);

  useEffect(() => {
    const selected = sampleClaims.find((sample) => sample.id === selectedSampleId);
    setClaimDraft(selected ? toClaimDraft(selected.claim) : null);
    setUploadError(null);
  }, [sampleClaims, selectedSampleId]);

  useEffect(() => {
    if (step !== 'processing' || !jobId) return;
    const interval = setInterval(() => {
      api.getScoringJob(jobId).then((job) => {
        setProcessingProgress(job.progressPercent);
        setActiveAnalysis(job.activeStage || 'Reviewing claim...');
        if (job.status === 'completed') {
          clearInterval(interval);
          api.getScoringResult(jobId).then((data) => {
            setResult(data);
            setStep('result');
          });
        }
        if (job.status === 'failed') {
          clearInterval(interval);
          setActiveAnalysis('Claim review failed.');
        }
      }).catch(() => undefined);
    }, 1200);
    return () => clearInterval(interval);
  }, [step, jobId]);

  useEffect(() => {
    const scrollDelay = step === 'result' ? 350 : 50;
    const scrollTimer = window.setTimeout(() => {
      if (step === 'processing') {
        processingSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      if (step === 'result') {
        resultsSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, scrollDelay);
    return () => window.clearTimeout(scrollTimer);
  }, [step]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="mx-auto max-w-6xl space-y-6 pb-12"
    >
      <div className="w-full">
        <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">Claim Fraud Check</h2>
        {/* <p className="text-slate-400 text-sm">Review a new claim for payment risk and investigation priority.</p> */}
      </div>

      <form onSubmit={analyzeClaim}>
        <GlassCard className="testcase-input-surface overflow-hidden p-0">
          <div className="border-b border-slate-800 px-5 py-5 sm:px-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div className="min-w-0">
                <div className="mb-3 flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-md border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
                    <FileText className="h-4 w-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">Testcase Claim Input</h3>
                    <p className="text-xs text-slate-400">Select a testcase and edit the fields before analysis.</p>
                  </div>
                </div>
                {selectedSample && (
                  <div className="text-xs text-slate-500">
                    Loaded from <span className="font-mono text-cyan-300">{selectedSample.filename}</span>
                  </div>
                )}
              </div>
              <label className="flex w-full flex-col gap-2 lg:max-w-sm">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  Testcase
                </span>
                <select
                  value={selectedSampleId}
                  disabled={sampleLoading || sampleClaims.length === 0}
                  onChange={(event) => selectSample(event.target.value)}
                  className="h-11 min-w-0 rounded-md border border-slate-700 bg-slate-950/60 px-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400 disabled:cursor-not-allowed disabled:text-slate-500"
                >
                  {sampleLoading && <option>Loading testcases...</option>}
                  {!sampleLoading && sampleClaims.length === 0 && <option>No JSON testcases found</option>}
                  {sampleClaims.map((sample) => (
                    <option key={sample.id} value={sample.id}>
                      {sample.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {uploadError && (
            <div className="mx-5 mt-5 rounded border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-200 sm:mx-6">
              {uploadError}
            </div>
          )}

          <div className="px-5 py-5 sm:px-6">
            {claimDraft ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {claimFields.map((field) => (
                  <label key={field.key} className="flex flex-col gap-2 text-left">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                      {field.label}
                    </span>
                    <input
                      type={field.type || 'text'}
                      step={field.type === 'number' ? 'any' : undefined}
                      value={claimDraft[field.key]}
                      required={['procedureCode', 'allowedAmount', 'providerId'].includes(field.key)}
                      onChange={(event) => setClaimDraft({ ...claimDraft, [field.key]: event.target.value })}
                      className="h-11 rounded-md border border-slate-700 bg-slate-950/60 px-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
                    />
                  </label>
                ))}
              </div>
            ) : (
              <div className="rounded-md border border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-400">
                {sampleLoading ? 'Loading testcase fields...' : 'No testcase claim is available.'}
              </div>
            )}
          </div>

          <div className="flex justify-end border-t border-slate-800 px-5 py-4 sm:px-6">
            <button
              type="submit"
              disabled={sampleLoading || !claimDraft || step === 'processing'}
              className="flex h-11 items-center justify-center gap-2 rounded-md bg-cyan-600 px-6 text-xs font-bold text-white shadow-[0_0_15px_rgba(8,145,178,0.3)] transition-colors hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {step === 'processing' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  ANALYZING
                </>
              ) : (
                <>
                  ANALYZE <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </div>
        </GlassCard>
      </form>

      <AnimatePresence>
        {step === 'processing' && (
          <motion.div
            ref={processingSectionRef}
            key="processing"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="w-full scroll-mt-6"
          >
            <GlassCard className="p-12 relative overflow-hidden">
              <motion.div
                animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
                transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
                className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-purple-600/5 to-cyan-500/5 opacity-50"
                style={{ backgroundSize: '200% 200%' }}
              />
              <div className="relative z-10 flex flex-col items-center text-center">
                <Loader2 className="w-16 h-16 text-cyan-400 animate-spin mb-6" />
                <h3 className="text-xl font-medium text-white mb-2">Reviewing Claim...</h3>
                <div className="font-mono text-cyan-400 text-sm min-h-6">{activeAnalysis}</div>
                <div className="w-full max-w-md h-2 bg-slate-800 rounded-full mt-8 overflow-hidden">
                  <motion.div
                    className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${processingProgress}%` }}
                    transition={{ ease: 'linear' }}
                  />
                </div>
                <div className="text-slate-500 font-mono text-xs mt-2">{processingProgress}% Review Progress</div>
              </div>
            </GlassCard>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {step === 'result' && result && (
          <motion.section
            ref={resultsSectionRef}
            key="result"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full scroll-mt-6 space-y-6"
          >
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
              <GlassCard className="lg:col-span-8 p-6 bg-gradient-to-br from-slate-900/80 to-slate-800/50 border-cyan-500/30">
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="font-bold text-white text-sm flex items-center gap-2">
                    <Zap className="w-4 h-4 text-cyan-400" /> AI Summary
                  </h3>
                  <span className={`w-fit text-[10px] font-bold border px-2 py-1 rounded ${aiSummary?.llmGenerated ? 'text-cyan-400 border-cyan-400/30 bg-cyan-400/10' : 'text-yellow-300 border-yellow-400/30 bg-yellow-400/10'}`}>
                    {aiSummary?.llmGenerated ? 'GENERATED SUMMARY' : 'STANDARD SUMMARY'}
                  </span>
                </div>
                <div className="text-sm text-slate-300 space-y-4">
                  <p>{aiSummary?.summary || 'No review summary returned for this claim.'}</p>
                  <div className="p-3 bg-slate-900/50 border border-slate-700 rounded text-xs space-y-2">
                    <div><strong className="text-cyan-400">Why this matters:</strong> {aiSummary?.riskReasoning || 'No risk explanation returned.'}</div>
                    <div><strong className="text-cyan-400">Recommendation:</strong> {aiSummary?.recommendation || 'No recommendation returned.'}</div>
                  </div>
                </div>
              </GlassCard>

              <div className="lg:col-span-4 flex flex-col gap-4">
                <GlassCard className="flex flex-col items-center p-6 relative overflow-hidden min-h-[360px] ring-1 ring-red-500/20 bg-slate-900/90">
                  <div className="absolute w-64 h-64 rounded-full blur-[100px] opacity-20 pointer-events-none bg-red-500" />
                  <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Review Priority</div>
                  <div className="relative w-44 h-44 mt-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={[{ value: fraudScore }, { value: 100 - fraudScore }]} cx="50%" cy="50%" startAngle={180} endAngle={0} innerRadius={64} outerRadius={82} dataKey="value" stroke="none">
                          <Cell fill="#ef4444" />
                          <Cell fill="rgba(255,255,255,0.05)" />
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                    <div className="absolute inset-0 flex flex-col items-center justify-center -mt-8">
                      <div className="text-5xl font-display font-bold text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]">{Math.round(fraudScore)}</div>
                      <div className="px-2 py-0.5 mt-2 text-xs font-bold bg-red-500/20 text-red-500 border border-red-500/30 rounded">{scoredClaim?.riskLevel || 'Unknown'} RISK</div>
                    </div>
                  </div>
                  <div className="w-full mt-2 z-10">
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 text-center">Process Insights</div>
                    <ul className="flex flex-wrap justify-center gap-2">
                      {processInsights.map((insight, index) => (
                        <li key={`${index}-${insight}`} className="flex max-w-full items-center gap-1.5 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-2.5 py-1 text-xs leading-snug text-slate-200">
                          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-400" />
                          <span>{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </GlassCard>

                <button
                  onClick={sendToInvestigationTeam}
                  disabled={!jobId || assignmentState === 'sending' || assignmentState === 'sent'}
                  className={`w-full flex h-12 items-center justify-center gap-2 rounded-md text-xs font-bold text-white shadow-[0_0_15px_rgba(8,145,178,0.3)] transition-all disabled:cursor-not-allowed ${
                    assignmentState === 'sent'
                      ? 'bg-emerald-600 shadow-[0_0_15px_rgba(5,150,105,0.3)]'
                      : assignmentState === 'error'
                        ? 'bg-red-600 hover:bg-red-500 shadow-[0_0_15px_rgba(220,38,38,0.25)]'
                        : 'bg-cyan-600 hover:bg-cyan-500'
                  }`}
                >
                  {assignmentState === 'sending' ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      SENDING EMAIL...
                    </>
                  ) : assignmentState === 'sent' ? (
                    <>
                      <CheckCircle className="h-4 w-4" />
                      EMAIL SENT TO INVESTIGATION TEAM
                    </>
                  ) : assignmentState === 'error' ? (
                    <>
                      <Mail className="h-4 w-4" />
                      EMAIL FAILED - TRY AGAIN
                    </>
                  ) : (
                    <>
                      <Mail className="h-4 w-4" />
                      SEND TO INVESTIGATION TEAM
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <GlassCard className="p-0 overflow-hidden border-orange-500/30 ring-1 ring-orange-500/10">
                <div className="px-6 py-4 bg-slate-900/60">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-orange-500/20 text-orange-500 flex items-center justify-center">
                      <ShieldAlert className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm">Rules Engine</h3>
                      <p className="text-xs text-slate-400">
                        {failedRuleCount > 0 ? `${failedRuleCount} check${failedRuleCount === 1 ? '' : 's'} need attention` : 'No rules violated'}
                      </p>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="min-h-[92px] bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center flex flex-col justify-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Checks Triggered</div>
                      <div className="text-3xl font-display font-bold text-orange-500">{failedRuleCount}</div>
                    </div>
                    <div className="min-h-[92px] bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center flex flex-col justify-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Severity</div>
                      <div className="text-3xl font-display font-bold text-white">{scoredAnalysis?.rulesAnalysis?.severity || 'Low'}</div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {triggeredRules.length > 0 ? (
                      triggeredRules.map((rule: any) => (
                        <div key={rule.ruleCode} className="p-3 bg-orange-500/10 border-l-2 border-orange-500 text-xs text-orange-100 rounded-r">
                          <span className="font-mono text-orange-400 font-bold mr-2">{rule.ruleCode}:</span> {rule.message}
                        </div>
                      ))
                    ) : (
                      <div className="p-3 bg-slate-900 border-l-2 border-slate-600 text-xs text-slate-300 rounded-r">
                        No rule violations related concerns for this claim.
                      </div>
                    )}
                  </div>
                </div>
              </GlassCard>

              <GlassCard className="p-0 overflow-hidden ring-1 ring-cyan-500/10">
                <div className="px-6 py-4 bg-slate-900/60">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                      <Activity className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm">Historical Comparison</h3>
                      <p className="text-xs text-slate-400">Claim is {String(claimHistoryLevel).toLowerCase()}</p>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="min-h-[92px] bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center flex flex-col justify-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Billing Pattern</div>
                      <div className="text-3xl font-display font-bold text-cyan-400">{claimHistoryLevel}</div>
                    </div>
                    <div className="min-h-[92px] bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center flex flex-col justify-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Score</div>
                      <div className="text-3xl font-display font-bold text-cyan-400">{Math.round(claimPatternScore)}/100</div>
                    </div>
                  </div>
                  <div className="md:col-span-2 text-xs text-slate-400 leading-relaxed p-3 bg-slate-900 rounded border border-slate-800">
                    <strong className="text-white">What this means:</strong> {historicalNarrative}
                  </div>
                </div>
              </GlassCard>

              <GlassCard className="p-0 overflow-hidden ring-1 ring-purple-500/10">
                <div className="px-6 py-4 bg-slate-900/60">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center">
                      <BrainCircuit className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm">Claim Pattern Analysis</h3>
                      <p className="text-xs text-slate-400">{scoreConcernLabel(mlAnomalyScore)} based on prior claim behavior</p>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Anomaly Detected</div>
                      <div className="text-3xl font-display font-bold text-purple-400">{scoreConcernLabel(mlAnomalyScore)}</div>
                    </div>
                    <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Score</div>
                      <div className="text-3xl font-display font-bold text-purple-400">{Math.round(mlAnomalyScore)}/100</div>
                    </div>
                    {/* <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Payment Behavior</div>
                      <div className="text-lg font-bold text-purple-400">{scoreConcernLabel(isolationForestScore)}</div>
                    </div>
                    <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                      <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Claim Detail Consistency</div>
                      <div className="text-lg font-bold text-purple-400">{scoreConcernLabel(pcaErrorScore)}</div>
                    </div> */}
                  </div>
                  <div className="text-xs text-slate-400 leading-relaxed p-3 bg-slate-900 rounded border border-slate-800">
                    <strong className="text-white">Pattern Summary:</strong> {patternNarrative}
                  </div>
                </div>
              </GlassCard>

              <GlassCard className="p-0 overflow-hidden ring-1 ring-emerald-500/10">
                <div className="px-6 py-4 bg-slate-900/60">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                      <Users className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm">Closest Similar Case</h3>
                      <p className="text-xs text-slate-400">{closestCase ? `Matched to ${closestCase.id} after scoring` : 'No processed historical match found'}</p>
                    </div>
                  </div>
                </div>
                <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                  {closestCase ? (
                    <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <span className="font-mono text-emerald-400 text-xs px-2 py-1 bg-emerald-500/20 rounded border border-emerald-500/30 w-fit">{closestCase.id}</span>
                        <span className="text-xs text-slate-400">
                          {closestCase.similarityScore != null ? `${Math.round(closestCase.similarityScore)}% profile match` : 'Processed historical match'}
                        </span>
                      </div>
                      <h4 className="text-white font-medium text-sm mt-3 mb-1">
                        {closestCase.procedureCode || 'N/A'} {closestCase.procedureDesc ? `- ${closestCase.procedureDesc}` : ''}
                      </h4>
                      <p className="text-xs text-emerald-100 mb-4">{closestCase.matchReason || 'Closest processed historical claim profile.'}</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div className="rounded border border-emerald-500/20 bg-slate-950/40 p-3">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Provider</div>
                          <div className="mt-1 text-slate-200">{closestCase.providerName || closestCase.providerId || 'N/A'}</div>
                        </div>
                        <div className="rounded border border-emerald-500/20 bg-slate-950/40 p-3">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Allowed Amount</div>
                          <div className="mt-1 text-slate-200">{formatCurrency(closestCase.allowedAmount)}</div>
                        </div>
                        <div className="rounded border border-emerald-500/20 bg-slate-950/40 p-3">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Prior Review Priority</div>
                          <div className="mt-1 text-slate-200">{closestCase.riskLevel || 'Low'} ({Math.round(Number(closestCase.fraudScore || 0))}/100)</div>
                        </div>
                        <div className="rounded border border-emerald-500/20 bg-slate-950/40 p-3">
                          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Closest Case Issue</div>
                          <div className="mt-1 text-slate-200">{closestCase.issueType || clusterAssignment?.cluster?.name || 'No significant issue'}</div>
                        </div>
                      </div>
                      <div className="mt-4 border-t border-emerald-500/20 pt-3 text-xs text-emerald-100">
                        <span className="font-semibold text-white">Known issue type:</span> {clusterAssignment?.cluster?.name || 'N/A'}
                        {clusterAssignment?.cluster?.riskCharacteristics ? ` - ${clusterAssignment?.cluster?.riskCharacteristics}` : ''}
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-lg text-sm text-slate-400">
                      No closest historical case was returned for this scored claim.
                    </div>
                  )}
                </div>
              </GlassCard>
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
