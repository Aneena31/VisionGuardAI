import React, { useEffect, useState } from 'react';
import { GlassCard, RiskBadge } from '../components/ui';
import { motion, AnimatePresence } from 'motion/react';
import { Search, CalendarDays, SlidersHorizontal, ChevronRight, RefreshCw, Database } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import type { Claim } from '../types';

const asText = (value: unknown, fallback = '') => (value === null || value === undefined ? fallback : String(value));
const asNumber = (value: unknown, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const normalizeClaim = (claim: any): Claim => ({
  id: asText(claim?.id, 'UNKNOWN'),
  providerId: asText(claim?.providerId),
  providerName: asText(claim?.providerName || claim?.providerId, 'Unknown Provider'),
  memberId: asText(claim?.memberId),
  procedureCode: asText(claim?.procedureCode, 'N/A'),
  procedureDesc: asText(claim?.procedureDesc),
  allowedAmount: asNumber(claim?.allowedAmount),
  fraudScore: asNumber(claim?.fraudScore),
  riskLevel: asText(claim?.riskLevel, 'Low') as Claim['riskLevel'],
  fraudType: claim?.fraudType ? asText(claim.fraudType) : null,
  clusterId: asText(claim?.clusterId, 'CL-00'),
  date: claim?.date ? asText(claim.date) : '',
  status: asText(claim?.status, 'Pending') as Claim['status'],
});

const normalizeClaims = (items: any) => (Array.isArray(items) ? items.map(normalizeClaim) : []);
const latestRetrain = () => {
  const client = api as any;
  const request = client.getLatestClaimsRetrain || client.getLatestSyncRetrain;
  return request ? request() : Promise.resolve({ run: null });
};
const startRetrain = () => {
  const client = api as any;
  const request = client.retrainClaimsModel || client.syncRetrainClaims;
  return request ? request() : Promise.reject(new Error('Retrain service unavailable.'));
};

export default function HistoricalClaimsExplorer() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('All');
  const [claims, setClaims] = useState<Claim[]>([]);
  const [pagination, setPagination] = useState({ page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
  const [retrainRun, setRetrainRun] = useState<any>(null);
  const [retrainMessage, setRetrainMessage] = useState('');

  useEffect(() => {
    const params = new URLSearchParams({ page: String(pagination.page), pageSize: '20' });
    if (searchTerm) params.set('search', searchTerm);
    if (riskFilter !== 'All') params.set('riskLevel', riskFilter);
    api.getClaims(`?${params.toString()}`)
      .then((data) => {
        setClaims(normalizeClaims(data?.items));
        setPagination(data?.pagination || { page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
      })
      .catch(() => {
        setClaims([]);
        setPagination({ page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
      });
  }, [searchTerm, riskFilter, pagination.page]);

  useEffect(() => {
    latestRetrain()
      .then((data) => setRetrainRun(data.run))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!retrainRun || !['queued', 'running'].includes(retrainRun.status)) return;

    const timer = window.setInterval(() => {
      latestRetrain()
        .then((data) => {
          setRetrainRun(data.run);
          if (data.run?.status === 'completed') {
            setRetrainMessage(`Retrain complete: ${data.run.claimsProcessed.toLocaleString()} workbook claims processed.`);
            api.getClaims('?page=1&pageSize=20')
              .then((claimsData) => {
                setClaims(normalizeClaims(claimsData?.items));
                setPagination(claimsData?.pagination || { page: 1, pageSize: 20, totalItems: 0, totalPages: 0 });
              })
              .catch(() => undefined);
          }
          if (data.run?.status === 'failed') {
            setRetrainMessage(data.run.errorMessage || 'Model retrain failed. Check the API logs for details.');
          }
        })
        .catch(() => undefined);
    }, 3000);

    return () => window.clearInterval(timer);
  }, [retrainRun?.id, retrainRun?.status]);

  const isRetraining = !!retrainRun && ['queued', 'running'].includes(retrainRun.status);
  const visibleClaims = normalizeClaims(claims);

  const handleRetrain = async () => {
    setRetrainMessage('');
    try {
      const data = await startRetrain();
      setRetrainRun(data.run);
      setRetrainMessage(data.message);
    } catch (error) {
      setRetrainMessage(error instanceof Error ? error.message : 'Unable to start model retrain.');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 h-full flex flex-col"
    >
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 shrink-0">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">Historical Claims Explorer</h2>
          <p className="text-slate-400 text-sm">Deep-dive into verified historical anomalies and flagged activity.</p>
        </div>
        <div className="flex flex-col items-start sm:items-end gap-2 w-full sm:w-auto">
          <button
            type="button"
            onClick={handleRetrain}
            disabled={isRetraining}
            className="bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-700 disabled:text-slate-400 text-slate-950 rounded-lg py-2 px-4 text-sm font-bold flex items-center justify-center gap-2 transition-colors w-full sm:w-auto"
          >
            {isRetraining ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
            {isRetraining ? 'Retraining' : 'Retrain'}
          </button>
          {(retrainMessage || retrainRun) && (
            <div className="text-xs text-slate-400 text-left sm:text-right max-w-[360px]">
              {retrainMessage || `Latest retrain: ${retrainRun.status}`}
            </div>
          )}
        </div>
      </div>

      <GlassCard className="p-4 flex flex-col md:flex-row gap-4 items-center shrink-0">
        <div className="flex-1 relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search Claim ID, Provider, Procedure..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPagination((current) => ({ ...current, page: 1 }));
            }}
            className="w-full bg-charcoal border border-glass-border rounded-lg py-2 pl-9 pr-4 text-sm focus:outline-none focus:border-neon-blue/50 text-white placeholder:text-slate-500"
          />
        </div>
        
        <div className="flex gap-4 w-full md:w-auto">
          <select 
            value={riskFilter}
            onChange={(e) => {
              setRiskFilter(e.target.value);
              setPagination((current) => ({ ...current, page: 1 }));
            }}
            className="bg-charcoal border border-glass-border rounded-lg py-2 px-4 text-sm text-white focus:outline-none appearance-none"
          >
            <option value="All">All Risks</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
          <button className="bg-charcoal border border-glass-border hover:bg-white/5 rounded-lg py-2 px-4 text-sm text-white flex items-center gap-2 transition-colors">
            <CalendarDays className="w-4 h-4" /> Date Range
          </button>
          <button className="bg-charcoal border border-glass-border hover:bg-white/5 rounded-lg py-2 px-4 text-sm text-white flex items-center gap-2 transition-colors">
             <SlidersHorizontal className="w-4 h-4" /> Advanced
          </button>
        </div>
      </GlassCard>

      <GlassCard className="flex-1 overflow-hidden flex flex-col p-0">
        <div className="px-6 py-3 border-b border-slate-800 text-xs text-slate-400 flex items-center justify-between">
          <span>
            Showing {visibleClaims.length} of {pagination.totalItems.toLocaleString()} claims
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPagination((current) => ({ ...current, page: Math.max(1, current.page - 1) }))}
              disabled={pagination.page <= 1}
              className="px-3 py-1 rounded-md bg-slate-900 disabled:opacity-40 text-white"
            >
              Prev
            </button>
            <span>Page {pagination.page} / {Math.max(pagination.totalPages, 1)}</span>
            <button
              type="button"
              onClick={() => setPagination((current) => ({ ...current, page: Math.min(Math.max(1, current.totalPages), current.page + 1) }))}
              disabled={pagination.page >= pagination.totalPages}
              className="px-3 py-1 rounded-md bg-slate-900 disabled:opacity-40 text-white"
            >
              Next
            </button>
          </div>
        </div>
        <div className="overflow-x-auto flex-1 h-full relative custom-scrollbar">
          <table className="w-full text-left border-collapse min-w-[900px]">
             <thead className="sticky top-0 bg-slate-950 text-[10px] uppercase font-bold text-slate-500 border-b border-slate-800 z-10">
               <tr>
                 <th className="py-3 px-6">Claim ID</th>
                 <th className="py-3 px-6">Provider</th>
                 <th className="py-3 px-6">Procedure</th>
                 <th className="py-3 px-6 text-right">Amount</th>
                 <th className="py-3 px-6 text-center">Score</th>
                 <th className="py-3 px-6">Risk Level</th>
                 <th className="py-3 px-6">Fraud Type</th>
                 <th className="py-3 px-6">Cluster</th>
                 <th className="py-3 px-6 text-right">Action</th>
               </tr>
             </thead>
             <tbody className="text-xs text-slate-300">
               <AnimatePresence>
                 {visibleClaims.map((claim, idx) => (
                   <motion.tr 
                     key={claim.id}
                     initial={{ opacity: 0, y: 10 }}
                     animate={{ opacity: 1, y: 0 }}
                     exit={{ opacity: 0 }}
                     transition={{ delay: idx * 0.01 }}
                     className="border-b border-slate-800/50 hover:bg-cyan-500/5 transition-colors group cursor-pointer"
                     onClick={() => navigate(`/claims/${claim.id}`)}
                   >
                     <td className="py-4 px-6 font-mono text-cyan-400">{claim.id}</td>
                     <td className="py-4 px-6 text-white max-w-[200px] truncate">{claim.providerName}</td>
                     <td className="py-4 px-6">
                        <span className="font-mono bg-slate-800 px-1.5 py-0.5 rounded mr-2">{claim.procedureCode}</span>
                        {claim.procedureDesc}
                     </td>
                     <td className="py-4 px-6 text-right font-mono">${claim.allowedAmount.toFixed(2)}</td>
                     <td className="py-4 px-6 text-center">
                       <div className={`mx-auto w-10 py-1 rounded text-center font-bold ${claim.fraudScore >= 80 ? 'bg-red-500 text-white' : claim.fraudScore >= 60 ? 'bg-orange-500 text-white' : 'bg-slate-700 text-slate-300'}`}>
                         {claim.fraudScore}
                       </div>
                     </td>
                     <td className="py-4 px-6">
                       <RiskBadge level={claim.riskLevel} />
                     </td>
                     <td className="py-4 px-6 text-orange-400">{claim.fraudType || 'N/A'}</td>
                     <td className="py-4 px-6">
                       <span className="font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-1 rounded">
                         {claim.clusterId}
                       </span>
                     </td>
                     <td className="py-4 px-6 text-right">
                       <button className="text-slate-500 group-hover:text-cyan-400 transition-colors p-1">
                          <ChevronRight className="w-4 h-4" />
                       </button>
                     </td>
                   </motion.tr>
                 ))}
               </AnimatePresence>
             </tbody>
          </table>
          {visibleClaims.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
              <Search className="w-12 h-12 mb-4 opacity-20" />
              <p>No claims found matching these criteria.</p>
            </div>
          )}
        </div>
      </GlassCard>
    </motion.div>
  );
}
