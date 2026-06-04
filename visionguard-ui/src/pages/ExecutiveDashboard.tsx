import React, { useEffect, useState } from 'react';
import { GlassCard } from '../components/ui';
import { motion } from 'motion/react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';
import { fraudTrendData as mockTrend, providers as mockProviders, claims as mockClaims } from '../data';
import { TrendingUp, AlertTriangle, Activity, DollarSign, Users, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

const COLORS = ['#00f3ff', '#bd00ff', '#00ffcc', '#ff007f'];
const RISK_COLORS = { 'Low': '#10b981', 'Medium': '#eab308', 'High': '#f97316', 'Critical': '#ef4444' };

export default function ExecutiveDashboard() {
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<any>(null);

  useEffect(() => {
    api.getDashboard().then(setDashboard).catch(() => setDashboard(null));
  }, []);

  const kpis = dashboard?.kpis;
  const fraudTrendData = dashboard?.fraudTrend?.length
    ? dashboard.fraudTrend.map((item: any) => ({ month: item.label, fraudAmount: item.fraudAmount, claims: item.claimCount }))
    : mockTrend;
  const providerRows = dashboard?.topSuspiciousProviders?.length ? dashboard.topSuspiciousProviders : mockProviders;
  const totalAnalyzed = dashboard?.riskDistribution?.totalAnalyzed ?? mockClaims.length;
  
  const riskDistribution = dashboard?.riskDistribution?.items?.length
    ? dashboard.riskDistribution.items.map((item: any) => ({ name: item.riskLevel, value: item.count }))
    : [
        { name: 'Low', value: mockClaims.filter(c => c.riskLevel === 'Low').length },
        { name: 'Medium', value: mockClaims.filter(c => c.riskLevel === 'Medium').length },
        { name: 'High', value: mockClaims.filter(c => c.riskLevel === 'High').length },
        { name: 'Critical', value: mockClaims.filter(c => c.riskLevel === 'Critical').length },
      ];

  const exportReport = () => {
    api.exportDashboard().catch(() => undefined);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -15 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1 tracking-tight">Executive Dashboard</h2>
          <p className="text-slate-400 text-sm">System status: <span className="text-cyan-400 uppercase tracking-widest text-[10px] font-bold">Optimized</span> &bull; System surveillance and AI risk analytics overview.</p>
        </div>
        <div className="flex gap-3 hidden md:flex">
          <button onClick={() => navigate('/scoring')} className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-md transition-all shadow-[0_0_15px_rgba(8,145,178,0.3)]">NEW CLAIM SCORING</button>
          <button onClick={exportReport} className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 text-xs font-bold rounded-md">EXPORT REPORT</button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Claims Analyzed', value: (kpis?.totalClaimsAnalyzed?.value ?? 45291).toLocaleString(), trend: `+${kpis?.totalClaimsAnalyzed?.trendPercent ?? 12}%`, icon: Activity, valueColor: 'text-white', trendColor: 'text-green-400', border: '' },
          { label: 'Total Allowed Amount', value: `$${Math.round((kpis?.totalAllowedAmount?.value ?? 4200000)).toLocaleString()}`, trend: `+${kpis?.totalAllowedAmount?.trendPercent ?? 5}%`, icon: DollarSign, valueColor: 'text-white', trendColor: 'text-green-400', border: '' },
          { label: 'Average Fraud Score', value: (kpis?.averageFraudScore?.value ?? 74.2).toFixed(1), trend: `+${kpis?.averageFraudScore?.trendPercent ?? 12.8}%`, icon: ShieldAlert, valueColor: 'text-orange-400', trendColor: 'text-red-400', border: 'ring-1 ring-orange-500/20' },
          { label: 'Critical Claims Flagged', value: (kpis?.criticalClaimsFlagged?.value ?? 312).toLocaleString(), trend: `${(kpis?.criticalClaimsFlagged?.shareOfTotalPercent ?? 2.1).toFixed(1)}%`, icon: AlertTriangle, valueColor: 'text-red-500', trendColor: 'text-slate-400', border: 'ring-1 ring-red-500/20' },
        ].map((kpi, idx) => (
          <GlassCard key={idx} className={`p-4 flex flex-col justify-between ${kpi.border}`}>
            <div className="flex justify-between items-start mb-2">
              <div className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">{kpi.label}</div>
              <div className="p-1.5 rounded-md bg-slate-800/50 text-slate-400 h-7 w-7 flex items-center justify-center">
                <kpi.icon className="w-3.5 h-3.5" />
              </div>
            </div>
            <div>
              <p className={`text-2xl font-bold ${kpi.valueColor}`}>{kpi.value}</p>
              <p className={`text-[10px] mt-1 font-mono uppercase ${kpi.trendColor}`}>
                {kpi.trend} {idx === 2 ? 'INCREASE DETECTED' : idx === 3 ? 'OF TOTAL VOLUME' : 'VS PREV PERIOD'}
              </p>
            </div>
          </GlassCard>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="lg:col-span-2 h-[400px] flex flex-col">
          <div className="px-1 py-1 mb-4 flex justify-between items-center">
            <span className="text-sm font-bold text-slate-200 tracking-wide uppercase">Detected Fraud Value Trend</span>
          </div>
          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={fraudTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorFraud" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#00f3ff" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#00f3ff" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="month" stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} axisLine={false} tickLine={false} />
                <YAxis stroke="#64748b" tick={{fill: '#64748b', fontSize: 12}} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val/1000}k`}/>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#12121a', borderColor: '#1f2937', borderRadius: '8px' }}
                  itemStyle={{ color: '#00f3ff' }}
                />
                <Area type="monotone" dataKey="fraudAmount" stroke="#00f3ff" strokeWidth={2} fillOpacity={1} fill="url(#colorFraud)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <GlassCard className="h-[400px] flex flex-col">
          <div className="px-1 py-1 mb-4 flex justify-between items-center">
            <span className="text-sm font-bold text-slate-200 tracking-wide uppercase">Risk Distribution</span>
          </div>
          <div className="flex-1 w-full min-h-0 flex items-center justify-center relative">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={riskDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {riskDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={RISK_COLORS[entry.name as keyof typeof RISK_COLORS]} />
                  ))}
                </Pie>
                <Tooltip 
                   contentStyle={{ backgroundColor: '#12121a', borderColor: '#1f2937', borderRadius: '8px' }}
                   itemStyle={{ color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Inner text for Donut */}
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-3xl font-bold text-white">{totalAnalyzed}</span>
              <span className="text-xs text-slate-400">Total Analyzed</span>
            </div>
          </div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 gap-6">
        <GlassCard>
           <div className="px-2 py-2 mb-4 flex justify-between items-center">
             <span className="text-sm font-bold text-slate-200 tracking-wide uppercase">Top Suspicious Providers</span>
           </div>
           <div className="overflow-x-auto custom-scrollbar">
             <table className="w-full text-left text-sm whitespace-nowrap">
               <thead className="bg-slate-950 text-[10px] uppercase font-bold text-slate-500 border-b border-slate-800">
                 <tr>
                   <th className="py-3 px-4">Provider ID</th>
                   <th className="py-3 px-4">Name</th>
                   <th className="py-3 px-4">Specialty</th>
                   <th className="py-3 px-4 text-center">Risk Score</th>
                   <th className="py-3 px-4">High Risk Ratio</th>
                   <th className="py-3 px-4 text-right">Allowed Amount</th>
                 </tr>
               </thead>
               <tbody className="text-xs text-slate-300">
                 {[...providerRows].sort((a,b) => b.riskScore - a.riskScore).slice(0, 5).map(provider => (
                   <tr 
                     key={provider.id} 
                     className="border-b border-slate-800/50 hover:bg-cyan-500/5 transition-colors cursor-pointer group"
                     onClick={() => navigate('/providers')}
                   >
                     <td className="py-4 px-4 font-mono text-cyan-400">{provider.id}</td>
                     <td className="py-4 px-4 font-medium text-white">{provider.name}</td>
                     <td className="py-4 px-4">{provider.specialty}</td>
                     <td className="py-4 px-4">
                       <div className={`mx-auto w-10 py-1 rounded text-center text-white font-bold ${provider.riskScore > 80 ? 'bg-red-500' : 'bg-orange-500'}`}>
                         {provider.riskScore}
                       </div>
                     </td>
                     <td className="py-4 px-4">{(provider.highRiskRatio * 100).toFixed(1)}%</td>
                     <td className="py-4 px-4 text-right font-mono">${provider.totalAllowedAmount.toLocaleString()}</td>
                   </tr>
                 ))}
               </tbody>
             </table>
           </div>
        </GlassCard>
      </div>
    </motion.div>
  );
}
