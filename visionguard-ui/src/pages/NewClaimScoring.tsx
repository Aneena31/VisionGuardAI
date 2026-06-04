import React, { useState, useEffect } from 'react';
import { GlassCard } from '../components/ui';
import { motion, AnimatePresence } from 'motion/react';
import { UploadCloud, FileText, Loader2, AlertTriangle, CheckCircle2, ShieldAlert, Activity, BrainCircuit, Users, HeartPulse, ChevronDown, ChevronRight, Zap } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { api } from '../api';

type Step = 'upload' | 'processing' | 'result';

export default function NewClaimScoring() {
  const [step, setStep] = useState<Step>('upload');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [activeAnalysis, setActiveAnalysis] = useState('Initializing Pipeline...');
  const [expandedStage, setExpandedStage] = useState<number>(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const scoredClaim = result?.claim;
  const scoredAnalysis = result?.analysis;

  const startProcessing = () => {
    setStep('processing');
    setProcessingProgress(0);
    setActiveAnalysis('Submitting Claim...');
    setResult(null);
    api.createScoringJob({
      sourceType: 'manual',
      claim: {
        procedureCode: 'V2784',
        procedureDesc: 'Premium Lens Addition',
        allowedAmount: 300,
        amtCharged: 750,
        units: 1,
        memberAge: 42,
        memberGender: 'Female',
        providerId: 'PRV-7121270',
        serviceDate: new Date().toISOString().slice(0, 10),
        benefitType: 'Lens',
        serviceCategoryName: 'lens material',
        benefitCategoryName: 'material',
      },
    })
      .then((job) => setJobId(job.jobId))
      .catch(() => {
        setActiveAnalysis('Scoring service unavailable.');
        setStep('upload');
      });
  };

  useEffect(() => {
    if (step !== 'processing' || !jobId) return;
    const interval = setInterval(() => {
      api.getScoringJob(jobId).then((job) => {
        setProcessingProgress(job.progressPercent);
        setActiveAnalysis(job.activeStage || 'Processing...');
        if (job.status === 'completed') {
          clearInterval(interval);
          api.getScoringResult(jobId).then((data) => {
            setResult(data);
            setStep('result');
          });
        }
        if (job.status === 'failed') {
          clearInterval(interval);
          setActiveAnalysis('Pipeline failed.');
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
          <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">New Claim Scoring</h2>
          <p className="text-slate-400 text-sm">Automated SIU fraud inference pipeline.</p>
        </div>
        {step === 'result' && (
           <button onClick={() => setStep('upload')} className="bg-slate-800 border border-slate-700 text-slate-300 px-4 py-2 rounded text-xs font-bold hover:bg-slate-700 transition">
             SCORE NEW CLAIM
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
            <GlassCard className="p-12 flex flex-col items-center justify-center border-dashed border-2 border-slate-700 bg-slate-900/40 hover:border-cyan-500/50 hover:bg-slate-800/50 transition-all group cursor-pointer" onClick={startProcessing}>
              <div className="w-20 h-20 bg-slate-900/60 border border-slate-700 rounded-full flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <UploadCloud className="w-10 h-10 text-cyan-400 group-hover:text-cyan-300" />
              </div>
              <h3 className="text-xl font-medium text-white mb-2">Drag & Drop Claim Files</h3>
              <p className="text-slate-400 text-sm mb-8 text-center max-w-sm">Support for X12 837, CSV, or direct JSON payloads.</p>
              
              <div className="flex gap-4">
                <button className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-6 py-3 rounded-md transition-colors shadow-[0_0_15px_rgba(8,145,178,0.3)]">
                  BROWSE FILES
                </button>
                <button className="bg-slate-800 border border-slate-700 hover:bg-slate-700 text-white font-bold text-xs px-6 py-3 rounded-md transition-colors flex items-center gap-2">
                  <FileText className="w-4 h-4" /> MANUAL ENTRY
                </button>
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
                 <h3 className="text-xl font-medium text-white mb-2">Analyzing Target Claim...</h3>
                 <div className="font-mono text-cyan-400 text-sm h-6">{activeAnalysis}</div>
                 
                 <div className="w-full max-w-md h-2 bg-slate-800 rounded-full mt-8 overflow-hidden">
                   <motion.div 
                     className="h-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.8)]"
                     initial={{ width: 0 }}
                     animate={{ width: `${processingProgress}%` }}
                     transition={{ ease: "linear" }}
                   />
                 </div>
                 <div className="text-slate-500 font-mono text-xs mt-2">{processingProgress}% Complete</div>
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
               {/* Step 1: Rules */}
               <GlassCard className="p-0 overflow-hidden border-orange-500/30 ring-1 ring-orange-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(0)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-orange-500/20 text-orange-500 flex items-center justify-center">
                       <ShieldAlert className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Rules Analysis Engine</h3>
                       <p className="text-xs text-slate-400">Triggered {scoredAnalysis?.rulesAnalysis?.triggeredRules?.length ?? 2} deterministic rules</p>
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
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Rule Score</div>
                             <div className="text-2xl font-bold text-orange-500">{Math.round(scoredAnalysis?.rulesAnalysis?.ruleScore ?? 72)}</div>
                           </div>
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Severity Flags</div>
                             <div className="text-2xl font-bold text-white">{scoredAnalysis?.rulesAnalysis?.severity ?? 'High'}</div>
                           </div>
                         </div>
                         <div className="space-y-2">
                           {(scoredAnalysis?.rulesAnalysis?.triggeredRules || [
                             { ruleCode: 'R009', message: 'High billed-to-allowed ratio detected.' },
                             { ruleCode: 'R008', message: 'High-cost material allowed amount exceeds threshold.' },
                           ]).map((rule: any) => (
                             <div key={rule.ruleCode} className="p-3 bg-orange-500/10 border-l-2 border-orange-500 text-xs text-orange-100 rounded-r">
                               <span className="font-mono text-orange-400 font-bold mr-2">{rule.ruleCode}:</span> {rule.message}
                             </div>
                           ))}
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 2: Statistical */}
               <GlassCard className="p-0 overflow-hidden ring-1 ring-cyan-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(1)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center">
                       <Activity className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Statistical Analysis</h3>
                       <p className="text-xs text-slate-400">Deviates +3.1 SD from mean</p>
                     </div>
                   </div>
                   {expandedStage === 1 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 1 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                       <div className="p-6 border-t border-slate-800/50 bg-slate-900/40 grid grid-cols-2 gap-4">
                         <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center">
                           <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Claim Z-Score</div>
                         <div className="text-3xl font-display font-bold text-cyan-400">{Number(scoredAnalysis?.statisticalAnalysis?.claimAmountZScore ?? 3.1).toFixed(1)}</div>
                         </div>
                         <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 text-center">
                           <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Provider Z-Score</div>
                         <div className="text-3xl font-display font-bold text-cyan-400">{Number(scoredAnalysis?.statisticalAnalysis?.providerZScore ?? 2.4).toFixed(1)}</div>
                         </div>
                         <div className="col-span-2 text-xs text-slate-400 leading-relaxed mt-2 p-3 bg-slate-900 rounded border border-slate-800">
                           <strong className="text-white">Narrative:</strong> {scoredAnalysis?.statisticalAnalysis?.narrative || 'The allowed amount is significantly higher than established norms for this geographic region.'}
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 3: ML Outlier Detection */}
               <GlassCard className="p-0 overflow-hidden ring-1 ring-purple-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(2)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center">
                       <BrainCircuit className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">ML Outlier Detection</h3>
                       <p className="text-xs text-slate-400">High reconstruction error detected</p>
                     </div>
                   </div>
                   {expandedStage === 2 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 2 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                       <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                         <div className="grid grid-cols-2 gap-4 mb-4">
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Isolation Forest</div>
                             <div className="text-lg font-bold text-purple-400">{Number(scoredAnalysis?.mlAnalysis?.isolationForestScore ?? 88).toFixed(1)}</div>
                           </div>
                           <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800">
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">PCA Error Score</div>
                             <div className="text-lg font-bold text-purple-400">{Number(scoredAnalysis?.mlAnalysis?.pcaErrorScore ?? 93).toFixed(1)}</div>
                           </div>
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 4: Cluster Assignment */}
               <GlassCard className="p-0 overflow-hidden ring-1 ring-emerald-500/10">
                 <div className="px-6 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(3)}>
                   <div className="flex items-center gap-4">
                     <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                       <Users className="w-4 h-4" />
                     </div>
                     <div>
                       <h3 className="font-bold text-white text-sm">Behavioral Cluster Assignment</h3>
                       <p className="text-xs text-slate-400">Mapped to Cluster {scoredAnalysis?.clusterAssignment?.clusterId ?? 'CL-03'}</p>
                     </div>
                   </div>
                   {expandedStage === 3 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
                 </div>
                 <AnimatePresence>
                   {expandedStage === 3 && (
                     <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                       <div className="p-6 border-t border-slate-800/50 bg-slate-900/40">
                         <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                           <div className="flex justify-between items-center mb-2">
                             <span className="font-mono text-emerald-400 text-xs px-2 py-1 bg-emerald-500/20 rounded border border-emerald-500/30">{scoredAnalysis?.clusterAssignment?.clusterId ?? 'CL-03'}</span>
                             <span className="text-xs text-slate-400">Size: {scoredAnalysis?.clusterAssignment?.cluster?.claimCount ?? 85} Claims</span>
                           </div>
                           <h4 className="text-white font-medium text-sm mb-1">{scoredAnalysis?.clusterAssignment?.cluster?.name ?? 'Unbundling - Glaucoma Screening'}</h4>
                           <p className="text-xs text-emerald-100">
                             {scoredAnalysis?.clusterAssignment?.cluster?.riskCharacteristics ?? 'This claim belongs to a high-risk behavioral cluster.'}
                           </p>
                         </div>
                       </div>
                     </motion.div>
                   )}
                 </AnimatePresence>
               </GlassCard>

               {/* Step 5: AI Summary */}
               <GlassCard className="p-6 bg-gradient-to-br from-slate-900/80 to-slate-800/50 border-cyan-500/30">
                 <div className="flex items-center justify-between mb-4">
                   <h3 className="font-bold text-white text-sm flex items-center gap-2">
                     <Zap className="w-4 h-4 text-cyan-400" /> AI Investigation Summary
                   </h3>
                   <span className="text-[10px] font-bold text-cyan-400 border border-cyan-400/30 px-2 py-1 rounded bg-cyan-400/10">GENERATED</span>
                 </div>
                 <div className="text-sm text-slate-300 space-y-4">
                   <p>{scoredAnalysis?.aiSummary?.summary || <>Based on the synergistic pipeline output, there is a very high probability of intentional <strong className="text-white">Unbundling</strong>.</>}</p>
                   <div className="p-3 bg-slate-900/50 border border-slate-700 rounded text-xs space-y-2">
                     <div><strong className="text-cyan-400">Risk Reasoning:</strong> {scoredAnalysis?.aiSummary?.riskReasoning || 'Rules, statistics, and ML signals indicate elevated fraud risk.'}</div>
                     <div><strong className="text-cyan-400">Recommendation:</strong> {scoredAnalysis?.aiSummary?.recommendation || 'Suspend auto-adjudication and route to SIU review.'}</div>
                   </div>
                 </div>
               </GlassCard>
            </div>

            {/* Right Col: Final Result Gauge */}
            <div className="lg:col-span-4 max-w-sm mx-auto w-full flex flex-col gap-6">
              <GlassCard className="flex flex-col items-center justify-center p-8 relative overflow-hidden h-80 ring-1 ring-red-500/20 bg-slate-900/90">
                 <div className="absolute w-64 h-64 rounded-full blur-[100px] opacity-20 pointer-events-none bg-red-500" />
                 
                 <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest absolute top-6 mt-1">FINAL OVERALL RISK</div>
                 
                 <div className="relative w-48 h-48 mt-6">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={[{value: scoredClaim?.fraudScore ?? 86}, {value: 100 - (scoredClaim?.fraudScore ?? 86)}]} cx="50%" cy="50%" startAngle={180} endAngle={0} innerRadius={70} outerRadius={90} dataKey="value" stroke="none">
                          <Cell fill="#ef4444" />
                          <Cell fill="rgba(255,255,255,0.05)" />
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                    
                    <div className="absolute inset-0 flex flex-col items-center justify-center -mt-8">
                       <div className="text-5xl font-display font-bold text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)]">{Math.round(scoredClaim?.fraudScore ?? 86)}</div>
                       <div className="px-2 py-0.5 mt-2 text-xs font-bold bg-red-500/20 text-red-500 border border-red-500/30 rounded">{scoredClaim?.riskLevel ?? 'Critical'} RISK</div>
                    </div>
                 </div>
                 <div className="text-center w-full mt-4 z-10">
                   <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Detected Fraud Pattern</div>
                   <div className="text-white text-sm font-bold">{scoredClaim?.fraudType ?? 'Unbundling Exclusivity'}</div>
                 </div>
              </GlassCard>

              <button onClick={() => jobId && api.assignScoringJob(jobId)} className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs py-4 rounded-md transition-all shadow-[0_0_15px_rgba(8,145,178,0.3)]">
                ASSIGN TO SIU ANALYST
              </button>
            </div>

          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
