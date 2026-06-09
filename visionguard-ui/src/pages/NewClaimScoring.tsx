import React, { useState, useEffect } from 'react';
import { GlassCard } from '../components/ui';
import { motion, AnimatePresence } from 'motion/react';
import { UploadCloud, FileText, Loader2, ShieldAlert, Activity, BrainCircuit, Users, ChevronDown, ChevronRight, Zap, ArrowRight, X, Mail, CheckCircle } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { api } from '../api';

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
  if (value >= 40) return 'Somewhat unusual';
  return 'Typical';
};

const scoreConcernLabel = (value: number) => {
  if (value >= 75) return 'High concern';
  if (value >= 50) return 'Needs review';
  if (value >= 25) return 'Watch';
  return 'Low concern';
};

const businessHistoricalNarrative = (rawNarrative: unknown, claimScore: number, providerScore: number) => {
  const narrative = typeof rawNarrative === 'string' ? rawNarrative.trim() : '';
  if (narrative && !technicalNarrativePattern.test(narrative)) return narrative;
  const claimLabel = historyConcernLabel(claimScore).toLowerCase();
  const providerLabel = historyConcernLabel(providerScore).toLowerCase();
  if (claimScore >= 70 && providerScore >= 70) {
    return 'Both the submitted claim and the provider billing profile are unusual compared with prior claim activity.';
  }
  if (claimScore >= 70) {
    return 'The submitted claim billing profile is unusual compared with prior claims with similar billing characteristics.';
  }
  if (providerScore >= 70) {
    return 'The provider billing profile is unusual compared with peer providers.';
  }
  if (claimScore >= 40 || providerScore >= 40) {
    return `The claim is ${claimLabel} and the provider is ${providerLabel}; this is worth a business review but is not a high-concern historical mismatch.`;
  }
  return 'The claim and provider look consistent with expected historical billing patterns.';
};

const businessPatternNarrative = (rawNarrative: unknown, patternScore: number) => {
  const narrative = typeof rawNarrative === 'string' ? rawNarrative.trim() : '';
  if (narrative && !technicalNarrativePattern.test(narrative)) return narrative;
  if (patternScore >= 75) {
    return 'The overall pattern score is high concern, which means the claim does not line up well with prior claim behavior and should be reviewed.';
  }
  if (patternScore >= 50) {
    return 'The overall pattern score needs review because the claim has noticeable differences from prior claim behavior.';
  }
  if (patternScore >= 25) {
    return 'The overall pattern score is on watch, with some differences from prior claim behavior.';
  }
  return 'The overall pattern score is low concern and remains consistent with prior claim behavior.';
};

const formatCurrency = (value: unknown) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value || 0));

export default function NewClaimScoring() {
  const [step, setStep] = useState<Step>('upload');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [activeAnalysis, setActiveAnalysis] = useState('Preparing claim review...');
  const [expandedStage, setExpandedStage] = useState<number>(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [sampleClaims, setSampleClaims] = useState<SampleClaim[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState('');
  const [sampleLoading, setSampleLoading] = useState(true);
  const [sampleModalOpen, setSampleModalOpen] = useState(false);
  const [claimDraft, setClaimDraft] = useState<ClaimDraft | null>(null);
  const [assignmentState, setAssignmentState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const scoredClaim = result?.claim;
  const scoredAnalysis = result?.analysis;
  const aiSummary = scoredAnalysis?.aiSummary;
  const triggeredRules = scoredAnalysis?.rulesAnalysis?.triggeredRules || [];
  const statisticalAnalysis = scoredAnalysis?.statisticalAnalysis || {};
  const mlAnalysis = scoredAnalysis?.mlAnalysis || {};
  const claimPatternScore = Number(statisticalAnalysis?.claimPatternScore ?? 0);
  const providerPatternScore = Number(statisticalAnalysis?.providerPatternScore ?? 0);
  const claimHistoryLevel = statisticalAnalysis?.claimPatternLevel || historyConcernLabel(claimPatternScore);
  const providerHistoryLevel = statisticalAnalysis?.providerPatternLevel || historyConcernLabel(providerPatternScore);
  const historicalNarrative = businessHistoricalNarrative(statisticalAnalysis?.narrative, claimPatternScore, providerPatternScore);
  const isolationForestScore = Number(mlAnalysis?.isolationForestScore || 0);
  const pcaErrorScore = Number(mlAnalysis?.pcaErrorScore || 0);
  const mlAnomalyScore = Number(mlAnalysis?.anomalyScore || 0);
  const patternNarrative = businessPatternNarrative(mlAnalysis?.modelSummary, mlAnomalyScore);
  const clusterAssignment = scoredAnalysis?.clusterAssignment;
  const closestCase = clusterAssignment?.closestCase;
  const fraudScore = Number(scoredClaim?.fraudScore || 0);

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

  const openSelectedSample = () => {
    const selected = sampleClaims.find((sample) => sample.id === selectedSampleId);
    if (!selected) {
      setUploadError('Choose a testcase before continuing.');
      return;
    }
    setClaimDraft(toClaimDraft(selected.claim));
    setSampleModalOpen(true);
    setUploadError(null);
  };

  const proceedWithSample = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!claimDraft) return;
    setSampleModalOpen(false);
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
      })
      .catch((error) => {
        setUploadError(error instanceof Error ? error.message : 'Failed to fetch testcases.');
      })
      .finally(() => setSampleLoading(false));
  }, []);

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

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={`mx-auto ${step === 'result' ? 'max-w-6xl' : 'max-w-4xl h-full flex flex-col items-center justify-center -mt-10'} space-y-6`}
    >
      <div className={`w-full ${step !== 'result' ? 'text-center xl:text-left xl:w-auto xl:mr-auto mb-4' : 'flex justify-between items-end'}`}>
        <div>
          <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">New Claim Review</h2>
          <p className="text-slate-400 text-sm">Review a new claim for payment risk and investigation priority.</p>
        </div>
        {step === 'result' && (
           <button onClick={() => setStep('upload')} className="bg-slate-800 border border-slate-700 text-slate-300 px-4 py-2 rounded text-xs font-bold hover:bg-slate-700 transition">
             REVIEW ANOTHER CLAIM
           </button>
        )}
      </div>

      <AnimatePresence mode="wait">
        {step === 'upload' && (
          <motion.div 
            key="upload"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
            className="w-full"
          >
            <GlassCard
              className="p-12 flex flex-col items-center justify-center border-dashed border-2 border-slate-700 bg-slate-900/40 hover:border-cyan-500/50 hover:bg-slate-800/50 transition-all group"
              onDragOver={(event) => event.preventDefault()}
            >
              <div className="w-20 h-20 bg-slate-900/60 border border-slate-700 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <UploadCloud className="w-10 h-10 text-cyan-400 group-hover:text-cyan-300" />
              </div>
              <h3 className="text-xl font-medium text-white mb-2">Select Testcase Claim</h3>
              <p className="text-slate-400 text-sm mb-8 text-center max-w-sm">Choose a testcase claim, review the input fields, then run the claim review.</p>
              {uploadError && (
                <div className="mb-5 max-w-md rounded border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-200">
                  {uploadError}
                </div>
              )}
              <div className="flex w-full max-w-xl flex-col gap-4 md:flex-row md:items-end md:justify-center">
                <div className="flex min-w-0 flex-1 flex-col gap-2">
                  <label className="text-left text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Testcase
                  </label>
                  <div className="flex min-w-0 gap-3">
                    <select
                      value={selectedSampleId}
                      disabled={sampleLoading || sampleClaims.length === 0}
                      onChange={(event) => setSelectedSampleId(event.target.value)}
                      className="h-11 min-w-0 flex-1 rounded-md border border-slate-700 bg-slate-950/60 px-3 text-sm text-slate-100 outline-none transition focus:border-cyan-400 disabled:cursor-not-allowed disabled:text-slate-500"
                    >
                      {sampleLoading && <option>Loading testcases...</option>}
                      {!sampleLoading && sampleClaims.length === 0 && <option>No JSON testcases found</option>}
                      {sampleClaims.map((sample) => (
                        <option key={sample.id} value={sample.id}>
                          {sample.label}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={openSelectedSample}
                      disabled={sampleLoading || sampleClaims.length === 0}
                      className="h-11 whitespace-nowrap bg-emerald-600 border border-emerald-400/30 hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60 text-white font-bold text-xs px-5 rounded-md transition-colors shadow-[0_0_15px_rgba(5,150,105,0.3)] flex items-center gap-2"
                    >
                      PROCEED <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {step === 'processing' && (
          <motion.div 
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
            className="w-full"
          >
            <GlassCard className="p-12 relative overflow-hidden">
               <motion.div 
                 animate={{ backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'] }}
                 transition={{ duration: 5, repeat: Infinity, ease: 'linear' }}
                 className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-purple-600/5 to-cyan-500/5 opacity-50"
                 style={{ backgroundSize: '200% 200%' }}
               />
               <div className="relative z-10 flex flex-col items-center">
                 <Loader2 className="w-16 h-16 text-cyan-400 animate-spin mb-6" />
                 <h3 className="text-xl font-medium text-white mb-2">Reviewing Claim...</h3>
                 <div className="font-mono text-cyan-400 text-sm h-6">{activeAnalysis}</div>
                 
                 <div className="w-full max-w-md h-2 bg-slate-800 rounded-full mt-8 overflow-hidden">
                   <motion.div 
                     className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)]"
                     initial={{ width: 0 }}
                     animate={{ width: `${processingProgress}%` }}
                     transition={{ ease: "linear" }}
                   />
                 </div>
                 <div className="text-slate-500 font-mono text-xs mt-2">{processingProgress}% Review Progress</div>
               </div>
            </GlassCard>
          </motion.div>
        )}

        {step === 'result' && (
          <motion.div 
            key="result"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6"
          >
            {/* Left Col: Timeline Workflow */}
            <div className="lg:col-span-8 flex flex-col gap-4">
               {/* Step 1: Rules engine */}
               <GlassCard className="p-0 overflow-hidden border-orange-500/30 ring-1 ring-orange-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(0)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-orange-500/20 text-orange-500 flex items-center justify-center">
                       <ShieldAlert className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Rules Engine</h3>
                       <p className="text-xs text-slate-400">
                         {triggeredRules.length > 0 ? `${triggeredRules.length} check${triggeredRules.length === 1 ? '' : 's'} need attention` : 'No policy issues found'}
                       </p>
                     </div>
                   </div>
                   {expandedStage === 0 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 0 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                       <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                         <div className="grid grid-cols-2 gap-4 mb-4">
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Billing Concern</div>
                             <div className="text-2xl font-bold text-orange-500">{scoreConcernLabel(Number(scoredAnalysis?.rulesAnalysis?.ruleScore || 0))}</div>
                           </div>
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Review Priority</div>
                             <div className="text-2xl font-bold text-white">{scoredAnalysis?.rulesAnalysis?.severity || 'Low'}</div>
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
                               No policy or billing checks raised concerns for this claim.
                             </div>
                           )}
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 2: Historical comparison */}
               <GlassCard className="p-0 overflow-hidden ring-1 ring-cyan-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(1)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                       <Activity className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Historical Comparison</h3>
                       <p className="text-xs text-slate-400">Claim is {String(claimHistoryLevel).toLowerCase()} | Provider is {String(providerHistoryLevel).toLowerCase()}</p>
                     </div>
                   </div>
                   {expandedStage === 1 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 1 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                       <div className="p-6 border-t border-slate-800/50 bg-slate-900/40 grid grid-cols-1 md:grid-cols-2 gap-4">
                         <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center">
                           <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Claim Billing vs History</div>
                           <div className="text-3xl font-display font-bold text-cyan-400">{claimHistoryLevel}</div>
                           <div className="mt-1 text-[11px] font-medium text-slate-500">Concern {Math.round(claimPatternScore)}/100</div>
                         </div>
                         <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center">
                           <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Provider Billing vs Peers</div>
                           <div className="text-3xl font-display font-bold text-cyan-400">{providerHistoryLevel}</div>
                           <div className="mt-1 text-[11px] font-medium text-slate-500">Concern {Math.round(providerPatternScore)}/100</div>
                         </div>
                         <div className="md:col-span-2 text-xs text-slate-400 leading-relaxed mt-2 p-3 bg-slate-900 rounded border border-slate-800">
                           <strong className="text-white">What this means:</strong> {historicalNarrative}
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 3: Pattern review */}
               <GlassCard className="p-0 overflow-hidden ring-1 ring-purple-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(2)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center">
                       <BrainCircuit className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Unusual Pattern Review</h3>
                       <p className="text-xs text-slate-400">{scoreConcernLabel(mlAnomalyScore)} based on prior claim behavior</p>
                     </div>
                   </div>
                   {expandedStage === 2 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 2 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                       <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                         <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Overall Pattern Concern</div>
                             <div className="text-lg font-bold text-purple-400">{scoreConcernLabel(mlAnomalyScore)}</div>
                             <div className="mt-1 text-[11px] font-medium text-slate-500">Score {Math.round(mlAnomalyScore)}/100</div>
                           </div>
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Payment Behavior</div>
                             <div className="text-lg font-bold text-purple-400">{scoreConcernLabel(isolationForestScore)}</div>
                           </div>
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Claim Detail Consistency</div>
                             <div className="text-lg font-bold text-purple-400">{scoreConcernLabel(pcaErrorScore)}</div>
                           </div>
                         </div>
                         <div className="text-xs text-slate-400 leading-relaxed p-3 bg-slate-900 rounded border border-slate-800">
                           <strong className="text-white">Pattern Summary:</strong> {patternNarrative}
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 4: Closest similar case */}
               <GlassCard className="p-0 overflow-hidden ring-1 ring-emerald-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(3)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                       <Users className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Closest Similar Case</h3>
                       <p className="text-xs text-slate-400">{closestCase ? `Matched to ${closestCase.id} after scoring` : 'No processed historical match found'}</p>
                     </div>
                   </div>
                   {expandedStage === 3 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 3 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
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
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 5: Review summary */}
               <GlassCard className="p-6 bg-gradient-to-br from-slate-900/80 to-slate-800/50 border-cyan-500/30">
                 <div className="flex items-center justify-between mb-4">
                   <h3 className="font-bold text-white text-sm flex items-center gap-2">
                     <Zap className="w-4 h-4 text-cyan-400" /> Review Summary
                   </h3>
                   <span className={`text-[10px] font-bold border px-2 py-1 rounded ${aiSummary?.llmGenerated ? 'text-cyan-400 border-cyan-400/30 bg-cyan-400/10' : 'text-yellow-300 border-yellow-400/30 bg-yellow-400/10'}`}>
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
            </div>

            {/* Right Col: Final Result Gauge */}
            <div className="lg:col-span-4 max-w-sm mx-auto w-full flex flex-col gap-6">
              <GlassCard className="flex flex-col items-center justify-center p-8 relative overflow-hidden h-80 ring-1 ring-red-500/20 bg-slate-900/90">
                 <div className="absolute w-64 h-64 rounded-full blur-[100px] opacity-20 pointer-events-none bg-red-500" />
                 
                 <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest absolute top-6 mt-1">REVIEW PRIORITY</div>
                 
                 <div className="relative w-48 h-48 mt-6">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={[{value: fraudScore}, {value: 100 - fraudScore}]} cx="50%" cy="50%" startAngle={180} endAngle={0} innerRadius={70} outerRadius={90} dataKey="value" stroke="none">
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
                 <div className="text-center w-full mt-4 z-10">
                   <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Likely Issue</div>
                   <div className="text-white text-sm font-bold">{scoredClaim?.fraudType || 'No Significant Concern Found'}</div>
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

          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {sampleModalOpen && claimDraft && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.form
              onSubmit={proceedWithSample}
              initial={{ opacity: 0, y: 18, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 18, scale: 0.98 }}
              className="w-full max-w-4xl"
            >
              <GlassCard className="max-h-[88vh] overflow-hidden p-0">
                <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-md border border-cyan-400/30 bg-cyan-400/10 text-cyan-300">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-white">Review Testcase Input</h3>
                      <p className="text-xs text-slate-400">Edit the claim fields before running the review.</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSampleModalOpen(false)}
                    className="flex h-9 w-9 items-center justify-center rounded-md border border-slate-700 bg-slate-900 text-slate-300 transition hover:bg-slate-800"
                    aria-label="Close testcase input"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="max-h-[calc(88vh-145px)] overflow-y-auto px-6 py-5">
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
                </div>

                <div className="flex flex-col-reverse gap-3 border-t border-slate-800 px-6 py-4 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    onClick={() => setSampleModalOpen(false)}
                    className="h-11 rounded-md border border-slate-700 bg-slate-900 px-5 text-xs font-bold text-slate-300 transition hover:bg-slate-800"
                  >
                    CANCEL
                  </button>
                  <button
                    type="submit"
                    className="flex h-11 items-center justify-center gap-2 rounded-md bg-cyan-600 px-6 text-xs font-bold text-white shadow-[0_0_15px_rgba(8,145,178,0.3)] transition-colors hover:bg-cyan-500"
                  >
                    PROCEED <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </GlassCard>
            </motion.form>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
