import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { GlassCard, RiskBadge } from '../components/ui';
import { motion, AnimatePresence } from 'motion/react';
import { claims, clusters } from '../data';
import { ArrowLeft, User, Stethoscope, Hash, ShieldAlert, Activity, BrainCircuit, Users, Zap, ChevronDown, ChevronRight } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { api } from '../api';

export default function ClaimInvestigationView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claimAnalysis, setClaimAnalysis] = useState<any>(null);
  const claim = claimAnalysis?.claim || claims.find(c => c.id === id) || claims[0];
  const analysis = claimAnalysis?.analysis;
  const cluster = analysis?.clusterAssignment?.cluster || clusters.find(c => c.id === claim.clusterId);
  const [expandedStage, setExpandedStage] = useState<number>(0);

  useEffect(() => {
    if (!id) return;
    api.getClaim(id).then(setClaimAnalysis).catch(() => setClaimAnalysis(null));
  }, [id]);

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    if (score >= 40) return '#eab308';
    return '#10b981';
  };

  const getScoreColorClass = (score: number) => {
    if (score >= 80) return 'text-red-500';
    if (score >= 60) return 'text-orange-500';
    if (score >= 40) return 'text-yellow-500';
    return 'text-green-500';
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => navigate(-1)}
            className="p-2 bg-slate-800 border border-slate-700 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-white tracking-tight">Investigation: {claim.id}</h2>
              <RiskBadge level={claim.riskLevel} />
            </div>
            <p className="text-slate-500 text-sm mt-0.5">Submitted on {claim.date} &bull; Pipeline execution completed</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="bg-slate-800 border border-slate-700 hover:bg-slate-700 text-white font-bold text-xs px-4 py-2 rounded transition-colors">
            DOWNLOAD REPORT
          </button>
          <button className="bg-red-500/20 border border-red-500/50 hover:bg-red-500/30 text-red-500 font-bold text-xs px-4 py-2 rounded transition-colors">
            FLAG FOR SIU
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Context Details */}
        <div className="lg:col-span-3 space-y-4">
          <GlassCard className="p-4 border-slate-800 bg-slate-900/60">
             <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
               <User className="w-3.5 h-3.5 text-cyan-400" /> Member Info
             </h3>
             <div className="space-y-3">
               <div>
                 <div className="text-[10px] text-slate-500 uppercase">Member ID</div>
                 <div className="font-mono text-white text-sm">{claim.memberId}</div>
               </div>
               <div className="flex justify-between">
                 <div>
                   <div className="text-[10px] text-slate-500 uppercase">Age</div>
                   <div className="text-white text-sm">{analysis?.member?.age ?? 42}</div>
                 </div>
                 <div>
                   <div className="text-[10px] text-slate-500 uppercase">Gender</div>
                   <div className="text-white text-sm">{analysis?.member?.gender || 'Male'}</div>
                 </div>
                 <div>
                   <div className="text-[10px] text-slate-500 uppercase">Location</div>
                   <div className="text-white text-sm">{analysis?.member?.location ? `${analysis.member.location.city}, ${analysis.member.location.state}` : 'Chicago, IL'}</div>
                 </div>
               </div>
             </div>
          </GlassCard>

          <GlassCard className="p-4 border-slate-800 bg-slate-900/60">
             <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
               <Stethoscope className="w-3.5 h-3.5 text-cyan-400" /> Provider Context
             </h3>
             <div className="space-y-3">
               <div>
                 <div className="text-[10px] text-slate-500 uppercase">Provider ID</div>
                 <div className="font-mono text-cyan-400 text-sm cursor-pointer hover:underline" onClick={() => navigate('/providers')}>{claim.providerId}</div>
               </div>
               <div>
                 <div className="text-[10px] text-slate-500 uppercase">Name</div>
                 <div className="text-white text-sm">{analysis?.providerContext?.providerName || claim.providerName}</div>
               </div>
               <div>
                 <div className="text-[10px] text-slate-500 uppercase">Z-Score History</div>
                 <div className="font-mono text-orange-400 text-sm">+{Number(analysis?.providerContext?.historicalZScore ?? 2.1).toFixed(1)} ({analysis?.providerContext?.historicalPercentile ?? 95}th Pctl)</div>
               </div>
             </div>
          </GlassCard>

          <GlassCard className="p-4 border-slate-800 bg-slate-900/60">
             <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
               <Hash className="w-3.5 h-3.5 text-cyan-400" /> Procedure Fact
             </h3>
             <div className="space-y-3">
               <div>
                 <div className="text-[10px] text-slate-500 uppercase mb-1">Code</div>
                 <div className="font-mono bg-slate-800 text-white text-xs inline-block px-2 py-1 rounded">{claim.procedureCode}</div>
               </div>
               <div>
                 <div className="text-[10px] text-slate-500 uppercase">Description</div>
                 <div className="text-white text-sm leading-snug">{claim.procedureDesc}</div>
               </div>
               <div>
                 <div className="text-[10px] text-slate-500 uppercase">Allowed Amount</div>
                 <div className="text-white font-mono text-lg font-bold">${claim.allowedAmount.toFixed(2)}</div>
               </div>
             </div>
          </GlassCard>
        </div>

        {/* Center Column: The Timeline */}
        <div className="lg:col-span-6 flex flex-col gap-4">
           {/* Step 1: Rules */}
           <div className="relative">
             <div className="absolute top-10 bottom-0 left-[27px] w-0.5 bg-slate-800 z-0"></div>
             <GlassCard className="p-0 overflow-hidden border-orange-500/30 ring-1 ring-orange-500/10 relative z-10">
               <div className="px-5 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(0)}>
                 <div className="flex items-center gap-4">
                   <div className="w-10 h-10 rounded-full bg-orange-500/20 text-orange-500 flex items-center justify-center shrink-0 border border-orange-500/30">
                     <ShieldAlert className="w-5 h-5" />
                   </div>
                   <div>
                     <h3 className="font-bold text-white text-sm">1. Rules Analysis</h3>
                     <p className="text-xs text-slate-400">Deterministic Engine &bull; {analysis?.rulesAnalysis?.status === 'triggered' || claim.fraudScore > 50 ? 'Flags Triggered' : 'Passed'}</p>
                   </div>
                 </div>
                 {expandedStage === 0 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
               </div>
               <AnimatePresence>
                 {expandedStage === 0 && (
                   <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                     <div className="p-5 border-t border-slate-800/50 bg-slate-900/40 ml-14">
                       <div className="space-y-2">
                         {analysis?.rulesAnalysis?.triggeredRules?.length ? (
                           analysis.rulesAnalysis.triggeredRules.map((rule: any) => (
                             <div key={rule.ruleCode} className="p-3 bg-orange-500/10 border-l-2 border-orange-500 text-xs text-orange-100 rounded-r">
                               <span className="font-mono text-orange-400 font-bold mr-2">{rule.ruleCode}:</span> {rule.message}
                             </div>
                           ))
                         ) : claim.fraudScore > 80 ? (
                           <>
                             <div className="p-3 bg-red-500/10 border-l-2 border-red-500 text-xs text-red-100 rounded-r">
                               <span className="font-mono text-red-400 font-bold mr-2">R-109:</span> Unbundling logic triggered for procedure {claim.procedureCode}.
                             </div>
                             <div className="p-3 bg-orange-500/10 border-l-2 border-orange-500 text-xs text-orange-100 rounded-r">
                               <span className="font-mono text-orange-400 font-bold mr-2">R-221:</span> Excessive frequency for provider peer group within 30 days.
                             </div>
                           </>
                         ) : claim.fraudScore > 50 ? (
                           <div className="p-3 bg-orange-500/10 border-l-2 border-orange-500 text-xs text-orange-100 rounded-r">
                             <span className="font-mono text-orange-400 font-bold mr-2">R-402:</span> High cost outlier compared to historical contracted rate.
                           </div>
                         ) : (
                           <div className="p-3 bg-green-500/10 border-l-2 border-green-500 text-xs text-green-100 rounded-r">
                             All standard deterministic rules passed. No immediate red flags.
                           </div>
                         )}
                       </div>
                     </div>
                   </motion.div>
                 )}
               </AnimatePresence>
             </GlassCard>
           </div>

           {/* Step 2: Statistical */}
           <div className="relative">
             <div className="absolute top-10 bottom-0 left-[27px] w-0.5 bg-slate-800 z-0"></div>
             <GlassCard className="p-0 overflow-hidden ring-1 ring-cyan-500/10 relative z-10">
               <div className="px-5 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(1)}>
                 <div className="flex items-center gap-4">
                   <div className="w-10 h-10 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 border border-cyan-500/30">
                     <Activity className="w-5 h-5" />
                   </div>
                   <div>
                     <h3 className="font-bold text-white text-sm">2. Statistical Analysis</h3>
                     <p className="text-xs text-slate-400">Distribution Outlier Profiling</p>
                   </div>
                 </div>
                 {expandedStage === 1 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
               </div>
               <AnimatePresence>
                 {expandedStage === 1 && (
                   <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                     <div className="p-5 border-t border-slate-800/50 bg-slate-900/40 grid grid-cols-2 gap-4 ml-14">
                       <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800 text-center">
                         <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Claim Amt Z-Score</div>
                         <div className={`text-2xl font-bold ${claim.fraudScore > 70 ? 'text-orange-400' : 'text-cyan-400'}`}>
                           {analysis?.statisticalAnalysis?.claimAmountZScore !== undefined ? Number(analysis.statisticalAnalysis.claimAmountZScore).toFixed(1) : claim.fraudScore > 70 ? '+3.1' : '+0.8'}
                         </div>
                       </div>
                       <div className="bg-slate-950/50 p-3 rounded-lg border border-slate-800 text-center">
                         <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Provider Z-Score</div>
                         <div className={`text-2xl font-bold ${claim.fraudScore > 60 ? 'text-red-400' : 'text-cyan-400'}`}>
                           {analysis?.statisticalAnalysis?.providerZScore !== undefined ? Number(analysis.statisticalAnalysis.providerZScore).toFixed(1) : claim.fraudScore > 60 ? '+2.4' : '-0.2'}
                         </div>
                       </div>
                     </div>
                   </motion.div>
                 )}
               </AnimatePresence>
             </GlassCard>
           </div>

           {/* Step 3: ML Detection */}
           <div className="relative">
             <div className="absolute top-10 bottom-0 left-[27px] w-0.5 bg-slate-800 z-0"></div>
             <GlassCard className="p-0 overflow-hidden ring-1 ring-purple-500/10 relative z-10">
               <div className="px-5 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(2)}>
                 <div className="flex items-center gap-4">
                   <div className="w-10 h-10 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/30">
                     <BrainCircuit className="w-5 h-5" />
                   </div>
                   <div>
                     <h3 className="font-bold text-white text-sm">3. ML Outlier Detection</h3>
                     <p className="text-xs text-slate-400">Isolation Forest &amp; PCA Ensembles</p>
                   </div>
                 </div>
                 {expandedStage === 2 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
               </div>
               <AnimatePresence>
                 {expandedStage === 2 && (
                   <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                     <div className="p-5 border-t border-slate-800/50 bg-slate-900/40 ml-14">
                         <div className="bg-slate-950/50 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
                           <div>
                             <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">ML Anomaly Score</div>
                             <div className="text-xs text-slate-400">Deep features reconstruction error</div>
                           </div>
                           <div className={`text-xl font-bold ${claim.fraudScore > 50 ? 'text-purple-400' : 'text-slate-300'}`}>
                             {Number((analysis?.mlAnalysis?.anomalyScore ?? claim.fraudScore) / 100).toFixed(2)}
                           </div>
                         </div>
                     </div>
                   </motion.div>
                 )}
               </AnimatePresence>
             </GlassCard>
           </div>

           {/* Step 4: Cluster Assignment */}
           <div className="relative">
             <div className="absolute top-10 bottom-0 left-[27px] w-0.5 bg-slate-800 z-0 hidden"></div>
             <GlassCard className="p-0 overflow-hidden ring-1 ring-emerald-500/10 relative z-10">
               <div className="px-5 py-4 flex items-center justify-between cursor-pointer bg-slate-900/60" onClick={() => setExpandedStage(3)}>
                 <div className="flex items-center gap-4">
                   <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/30">
                     <Users className="w-5 h-5" />
                   </div>
                   <div>
                     <h3 className="font-bold text-white text-sm">4. Behavioral Cluster Assignment</h3>
                     <p className="text-xs text-slate-400">Mapped to {analysis?.clusterAssignment?.clusterId || (cluster ? cluster.id : 'None')}</p>
                   </div>
                 </div>
                 {expandedStage === 3 ? <ChevronDown className="w-5 h-5 text-slate-500" /> : <ChevronRight className="w-5 h-5 text-slate-500" />}
               </div>
               <AnimatePresence>
                 {expandedStage === 3 && (
                   <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
                     <div className="p-5 border-t border-slate-800/50 bg-slate-900/40 ml-14">
                       {cluster ? (
                         <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                           <div className="flex justify-between items-center mb-2">
                             <span className="font-mono text-emerald-400 text-xs px-2 py-1 bg-emerald-500/20 rounded border border-emerald-500/30">{cluster.id}</span>
                           </div>
                           <h4 className="text-white font-medium text-sm mb-1">{cluster.name}</h4>
                           <p className="text-xs text-emerald-100">{cluster.riskCharacteristics}</p>
                         </div>
                       ) : (
                         <div className="text-sm text-slate-400">Did not map to a recognized high-risk behavioral cluster.</div>
                       )}
                     </div>
                   </motion.div>
                 )}
               </AnimatePresence>
             </GlassCard>
           </div>

           {/* Step 5: AI Summary */}
           <GlassCard className="p-6 bg-gradient-to-br from-slate-900/80 to-slate-800/50 border-cyan-500/30 ml-4 relative z-10 shadow-[0_0_20px_rgba(34,211,238,0.1)]">
             <div className="flex items-center justify-between mb-4">
               <h3 className="font-bold text-white text-sm flex items-center gap-2">
                 <Zap className="w-4 h-4 text-cyan-400" /> Synthesized AI Summary
               </h3>
               <span className="text-[10px] font-bold text-cyan-400 border border-cyan-400/30 px-2 py-1 rounded bg-cyan-400/10">FINAL STAGE</span>
             </div>
             <div className="text-sm text-slate-300 space-y-4">
               {analysis?.aiSummary ? (
                 <>
                   <p>{analysis.aiSummary.summary}</p>
                   <div className="p-3 bg-slate-900/80 border border-slate-700 rounded text-xs space-y-2">
                     <div><strong className="text-cyan-400">Risk Reasoning:</strong> {analysis.aiSummary.riskReasoning}</div>
                     <div><strong className="text-cyan-400">Recommendation:</strong> {analysis.aiSummary.recommendation}</div>
                   </div>
                 </>
               ) : claim.fraudScore >= 80 ? (
                 <>
                   <p>Based on the synergistic pipeline output, there is a dominant probability of intentional <strong className="text-white">{claim.fraudType || 'Abuse'}</strong>.</p>
                   <div className="p-3 bg-slate-900/80 border border-slate-700 rounded text-xs space-y-2">
                     <div><strong className="text-cyan-400">Risk Reasoning:</strong> Procedure {claim.procedureCode} generated severe ML reconstruction errors and aligns with behavioral cluster {claim.clusterId}.</div>
                     <div><strong className="text-cyan-400">Recommendation:</strong> Route to Special Investigations Unit immediately.</div>
                   </div>
                 </>
               ) : claim.fraudScore >= 60 ? (
                 <>
                   <p>The pipeline has identified elevated, but not critical, patterns of <strong className="text-white">{claim.fraudType || 'Upcoding'}</strong>.</p>
                   <div className="p-3 bg-slate-900/80 border border-slate-700 rounded text-xs space-y-2">
                     <div><strong className="text-cyan-400">Risk Reasoning:</strong> Deterministic rules were breached on historical peer velocity. However, ML certainty is moderate.</div>
                     <div><strong className="text-cyan-400">Recommendation:</strong> Proceed with soft denial code pending standard appeal, or subject to automated record request logic.</div>
                   </div>
                 </>
               ) : (
                 <>
                   <p>The claim exhibits normal statistical variance and conforms to expected clinical/financial distributions.</p>
                   <div className="p-3 bg-slate-900/80 border border-slate-700 rounded text-xs space-y-2">
                     <div><strong className="text-cyan-400">Risk Reasoning:</strong> All pipelines report acceptable confidence internals.</div>
                     <div><strong className="text-cyan-400">Recommendation:</strong> Clear for standard auto-adjudication rails.</div>
                   </div>
                 </>
               )}
             </div>
           </GlassCard>
        </div>

        {/* Right Column: Final Score Gauge */}
        <div className="lg:col-span-3 space-y-6">
          <GlassCard className="flex flex-col items-center justify-center p-6 relative overflow-hidden h-[360px] bg-slate-900/90 border-slate-800">
             <div className="absolute w-64 h-64 rounded-full blur-[100px] opacity-10 pointer-events-none" style={{ backgroundColor: getScoreColor(claim.fraudScore) }} />
             
             <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest absolute top-6 mt-1">Calculated AI Score</div>
             
             <div className="relative w-48 h-48 mt-6">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={[{value: claim.fraudScore}, {value: 100 - claim.fraudScore}]} cx="50%" cy="50%" startAngle={180} endAngle={0} innerRadius={70} outerRadius={90} dataKey="value" stroke="none">
                      <Cell fill={getScoreColor(claim.fraudScore)} />
                      <Cell fill="rgba(255,255,255,0.05)" />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
                
                <div className="absolute inset-0 flex flex-col items-center justify-center -mt-8">
                   <div className={`text-6xl font-bold drop-shadow-[0_0_15px_rgba(255,255,255,0.1)] ${getScoreColorClass(claim.fraudScore)}`}>
                     {claim.fraudScore}
                   </div>
                   <div className={`px-2 py-0.5 mt-2 text-[10px] uppercase font-bold rounded ${claim.fraudScore >= 80 ? 'bg-red-500/20 text-red-500 border border-red-500/30' : claim.fraudScore >= 60 ? 'bg-orange-500/20 text-orange-500 border border-orange-500/30' : 'bg-green-500/20 text-green-500 border border-green-500/30'}`}>
                     {claim.riskLevel} RISK
                   </div>
                </div>
             </div>
             <div className="text-center w-full mt-2 z-10">
               <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Detected Fraud Pattern</div>
               <div className="text-white text-sm font-bold">{claim.fraudType || 'Standard Baseline'}</div>
             </div>
          </GlassCard>
        </div>
      </div>
    </motion.div>
  );
}
