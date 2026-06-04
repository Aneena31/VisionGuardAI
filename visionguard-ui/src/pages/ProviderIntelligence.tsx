import React, { useEffect, useState } from 'react';
import { GlassCard } from '../components/ui';
import { motion, AnimatePresence } from 'motion/react';
import { providers as mockProviders } from '../data';
import { Search, MapPin, Activity, Stethoscope, Briefcase, TrendingUp } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, Tooltip, CartesianGrid, YAxis } from 'recharts';
import { api } from '../api';

export default function ProviderIntelligence() {
  const [providers, setProviders] = useState(mockProviders);
  const [selectedProvider, setSelectedProvider] = useState(mockProviders[1]);
  const [providerDetail, setProviderDetail] = useState<any>(null);
  const [liveProvidersLoaded, setLiveProvidersLoaded] = useState(false);

  useEffect(() => {
    api.getProviders('?pageSize=100')
      .then((data) => {
        const rows = data.items?.length ? data.items : mockProviders;
        setProviders(rows);
        setSelectedProvider(rows[0]);
        setLiveProvidersLoaded(true);
      })
      .catch(() => setProviders(mockProviders));
  }, []);

  useEffect(() => {
    if (!selectedProvider?.id || !liveProvidersLoaded) return;
    api.getProvider(selectedProvider.id).then(setProviderDetail).catch(() => setProviderDetail(null));
  }, [selectedProvider?.id, liveProvidersLoaded]);

  const peerData = providerDetail?.procedurePeerComparison?.length
    ? providerDetail.procedurePeerComparison.map((item: any) => ({
        name: item.procedureCode,
        provider: item.providerVolume,
        peer: item.peerAverageVolume,
      }))
    : [
        { name: '92004', provider: 120, peer: 45 },
        { name: '92014', provider: 80, peer: 90 },
        { name: '92250', provider: 65, peer: 20 },
        { name: 'V2784', provider: 150, peer: 30 },
      ];
  const aiSummary = providerDetail?.aiSummary;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      className="space-y-6 h-full flex flex-col"
    >
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h2 className="text-3xl font-display font-bold text-white mb-2">Provider Intelligence</h2>
          <p className="text-slate-400">Behavioral profiling and peer comparative risk analysis.</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Find provider..."
            className="bg-charcoal border border-glass-border rounded-lg py-2 pl-9 pr-4 text-sm w-64 focus:outline-none focus:border-neon-purple/50 text-white placeholder:text-slate-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 min-h-0">
        <GlassCard className="lg:col-span-4 flex flex-col p-0 overflow-hidden">
           <div className="bg-charcoal/50 p-4 border-b border-glass-border">
             <h3 className="font-semibold text-white">Monitored Entities</h3>
           </div>
           <div className="flex-1 overflow-y-auto custom-scrollbar">
             {providers.map((p) => (
               <div 
                 key={p.id} 
                 onClick={() => setSelectedProvider(p)}
                 className={`p-4 border-b border-glass-border/30 cursor-pointer transition-colors relative ${selectedProvider.id === p.id ? 'bg-neon-blue/10' : 'hover:bg-white/5'}`}
               >
                 {selectedProvider.id === p.id && (
                   <motion.div layoutId="activeProvider" className="absolute left-0 top-0 w-1 h-full bg-neon-blue" />
                 )}
                 <div className="flex justify-between items-start mb-1">
                   <div className="font-medium text-white">{p.name}</div>
                   <div className={`text-xs font-bold px-1.5 py-0.5 rounded ${p.riskScore > 80 ? 'bg-red-500/20 text-red-400' : p.riskScore > 50 ? 'bg-orange-500/20 text-orange-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                     {p.riskScore}
                   </div>
                 </div>
                 <div className="text-xs text-slate-400 font-mono mb-2">{p.id}</div>
                 <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="flex items-center gap-1"><MapPin className="w-3 h-3"/> {p.city}, {p.state}</span>
                    <span className="flex items-center gap-1"><Stethoscope className="w-3 h-3"/> {p.specialty}</span>
                 </div>
               </div>
             ))}
           </div>
        </GlassCard>

        <div className="lg:col-span-8 space-y-6 overflow-y-auto custom-scrollbar pr-2">
          {/* Provider Detail Header */}
          <GlassCard className="p-8 relative overflow-hidden bg-gradient-to-br from-charcoal via-charcoal to-neon-purple/10">
            <div className="absolute top-0 right-0 w-64 h-64 bg-neon-purple/20 blur-[100px] rounded-full pointer-events-none" />
            
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <h2 className="text-3xl font-display font-bold text-white shadow-neon-purple/50">{selectedProvider.name}</h2>
                  {selectedProvider.riskScore > 80 && (
                    <span className="bg-red-500/20 border border-red-500/50 text-red-500 px-2 py-0.5 rounded text-xs font-bold animate-pulse">HIGH RISK</span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-sm text-slate-300 font-mono">
                  <span>{selectedProvider.id}</span>
                  <span className="flex items-center gap-1"><Stethoscope className="w-4 h-4 text-neon-blue" /> {selectedProvider.specialty}</span>
                  <span className="flex items-center gap-1"><MapPin className="w-4 h-4 text-neon-blue" /> {selectedProvider.city}, {selectedProvider.state}</span>
                </div>
              </div>
              <div className="text-center">
                 <div className="text-sm text-slate-400 uppercase tracking-widest mb-1">Risk Score</div>
                 <div className="text-5xl font-display font-bold text-white">{selectedProvider.riskScore}</div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 mt-8">
               <div className="bg-glass border border-glass-border p-4 rounded-lg">
                 <div className="text-xs text-slate-400 mb-1">Total Claims (12mo)</div>
                 <div className="text-xl font-medium text-white">{selectedProvider.claimCount}</div>
               </div>
               <div className="bg-glass border border-glass-border p-4 rounded-lg">
                 <div className="text-xs text-slate-400 mb-1">High Risk Ratio</div>
                 <div className="text-xl font-medium text-white">{(selectedProvider.highRiskRatio * 100).toFixed(1)}%</div>
               </div>
               <div className="bg-glass border border-glass-border p-4 rounded-lg">
                 <div className="text-xs text-slate-400 mb-1">Total Allowed Amount</div>
                 <div className="text-xl font-mono text-neon-cyan">${selectedProvider.totalAllowedAmount.toLocaleString()}</div>
               </div>
            </div>
          </GlassCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <GlassCard className="h-80 flex flex-col">
              <h3 className="font-semibold text-white mb-4">Procedure Volume vs Peer Average</h3>
              <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={peerData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                    <XAxis dataKey="name" stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} />
                    <YAxis stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} />
                    <Tooltip contentStyle={{ backgroundColor: '#12121a', borderColor: '#1f2937' }} cursor={{fill: 'rgba(255,255,255,0.05)'}} />
                    <Bar dataKey="provider" fill="#00f3ff" name="Provider Vol" radius={[4,4,0,0]} />
                    <Bar dataKey="peer" fill="#334155" name="Peer Avg Vol" radius={[4,4,0,0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </GlassCard>

            <GlassCard>
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-neon-blue" /> AI Analysis Summary
              </h3>
              <div className="space-y-4 text-sm text-slate-300 leading-relaxed">
                <p>
                  <span className="text-white font-medium">Pattern Deviation:</span> {aiSummary?.patternDeviation || `${selectedProvider.name} exhibits a significant deviation from regional peers in premium service billing.`}
                </p>
                <p>
                  <span className="text-white font-medium">Velocity Indicator:</span> {aiSummary?.velocityIndicator || 'Claim submission volume for premium services has increased beyond expected peer trends.'}
                </p>
                <div className="p-3 bg-neon-purple/10 border border-neon-purple/20 rounded-lg text-neon-purple mt-4 font-medium">
                  Recommendation: {aiSummary?.recommendation || 'Initiate targeted audit for medical necessity documentation.'}
                </div>
              </div>
            </GlassCard>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
