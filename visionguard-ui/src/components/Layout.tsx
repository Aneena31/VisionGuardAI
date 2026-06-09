import React, { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { BarChart3, Search, Users, Upload, Bell, ChevronRight, Zap, Moon, Sun } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from './ui';
import { api } from '../api';

const NAV_ITEMS = [
  { name: 'Executive Dashboard', path: '/', icon: BarChart3 },
  { name: 'Claims Explorer', path: '/claims', icon: Search },
  { name: 'Provider Intelligence', path: '/providers', icon: Users },
  { name: 'New Claim Scoring', path: '/scoring', icon: Upload },
];

export function Layout() {
  const location = useLocation();
  const [systemStatus, setSystemStatus] = useState({ modelAi: 'OFFLINE', pipeline: 'STALE' });
  const [unreadCount, setUnreadCount] = useState(0);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    api.getSystemStatus().then(setSystemStatus).catch(() => undefined);
    api.getNotifications().then((data) => setUnreadCount(data.unreadCount || 0)).catch(() => undefined);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('theme-light', theme === 'light');
    window.localStorage.setItem('visionguard-theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((current) => current === 'dark' ? 'light' : 'dark');

  return (
    <div className="flex h-screen w-full bg-[#05070a] text-slate-300 overflow-hidden relative font-sans">
      {/* Background ambient dotted grid */}
      <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(#00f2ff 1px, transparent 1px)', backgroundSize: '32px 32px' }} />

      {/* Sidebar */}
      <nav className="w-64 border-r border-cyan-500/10 bg-slate-900/20 backdrop-blur-sm flex flex-col z-10 shrink-0">
        <div className="h-14 flex items-center px-6 border-b border-cyan-500/20">
          <img src="/visionguard-logo.svg" alt="VisionGuard AI" className="w-8 h-8 mr-3 shrink-0" />
          <h1 className="font-display font-bold text-xl tracking-tight text-white drop-shadow-[0_0_8px_rgba(0,242,255,0.7)]">
            VisionGuard <span className="text-cyan-400">AI</span>
          </h1>
        </div>

        <div className="flex-1 py-6 flex flex-col gap-2 px-3 overflow-y-auto">
          <div className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-2 px-3">Analytics & Operations</div>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group relative',
                  isActive
                    ? 'text-white bg-cyan-400/10'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon className={cn("w-5 h-5", isActive ? "text-cyan-400" : "text-slate-500 group-hover:text-cyan-400")} />
                  {item.name}
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-2/3 bg-cyan-400 rounded-r-full shadow-[0_0_10px_rgba(0,242,255,0.8)]"
                      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </div>
        
        <div className="p-4 border-t border-glass-border">
          <div className="bg-slate-900/40 rounded-lg border border-slate-700/50 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-bold text-slate-200">System Status</span>
            </div>
            <div className="text-xs font-mono text-slate-400">
              <div className="flex justify-between items-center mb-1">
                <span>Model AI:</span>
                <span className="text-cyan-400">{systemStatus.modelAi}</span>
              </div>
              <div className="flex justify-between items-center">
                <span>Pipeline:</span>
                <span className="text-cyan-400">{systemStatus.pipeline}</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 z-10">
        <header className="h-14 flex items-center justify-between px-6 border-b border-cyan-500/20 bg-slate-900/40 backdrop-blur-md">
          <div className="flex items-center gap-4 text-sm font-medium">
             <span className="opacity-60">SOC Workspace</span>
             <ChevronRight className="w-4 h-4 opacity-40" />
             <span className="text-cyan-400 capitalize">
               {location.pathname === '/' ? 'Executive Dashboard' : location.pathname.substring(1).replace('-', ' ')}
             </span>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="relative flex items-center bg-slate-950/50 border border-slate-700 rounded-full px-4 py-1.5 w-80">
              <Search className="w-4 h-4 text-slate-500 mr-2 shrink-0" />
              <input 
                type="text" 
                placeholder="Search Claim IDs, Providers..." 
                className="bg-transparent border-none text-sm focus:outline-none w-full text-slate-200 placeholder:text-slate-500 transition-colors"
              />
            </div>
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              aria-pressed={theme === 'light'}
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
              className="h-9 rounded-full border border-slate-700 bg-slate-950/50 px-3 text-xs font-bold uppercase tracking-wide text-slate-300 hover:text-white hover:bg-slate-800/50 transition-colors flex items-center gap-2"
            >
              {theme === 'dark' ? <Moon className="w-4 h-4 text-cyan-400" /> : <Sun className="w-4 h-4 text-cyan-500" />}
              {theme === 'dark' ? 'Dark' : 'Light'}
            </button>
            <div className="relative cursor-pointer">
              <Bell className="w-6 h-6 text-slate-400 hover:text-white transition-colors" />
              {unreadCount > 0 && <div className="absolute -top-1 -right-1 min-w-4 h-4 px-1 bg-red-500 rounded-full text-[9px] text-white flex items-center justify-center">{unreadCount}</div>}
            </div>
            <div className="w-8 h-8 rounded-full border border-cyan-400/50 bg-slate-800 flex items-center justify-center font-bold text-xs uppercase text-cyan-400" title="Investigator Profile">
              JD
            </div>
          </div>
        </header>
        
        <main className="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
          <AnimatePresence mode="wait">
            <Outlet />
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}
