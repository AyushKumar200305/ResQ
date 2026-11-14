import React from "react";
import {
  Activity,
  AlertCircle,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Database,
  GraduationCap,
  LogOut,
  Menu,
  Radio,
  ShieldAlert,
  UserCheck,
  X,
} from "lucide-react";
import { useApp } from "../../context/AppContext";

export const Header: React.FC = () => {
  const {
    user,
    network,
    analysis,
    presets,
    loadPreset,
    loadDemo,
    logout,
    runFullAnalysis,
    openPresentation,
    openLexicon,
    isMobileNavOpen,
    toggleMobileNav,
    isLoading,
  } = useApp();

  const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const key = e.target.value;
    if (key === "__demo__") {
      loadDemo();
    } else if (key) {
      loadPreset(key);
    }
  };

  return (
    <header className="h-16 bg-white/95 backdrop-blur border-b border-slate-200 shadow-xs px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Brand & Incident Command Status */}
      <div className="flex items-center gap-3 md:gap-4">
        {/* Mobile Hamburger Drawer Button */}
        <button
          onClick={toggleMobileNav}
          className="md:hidden p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
          title="Toggle Navigation Menu"
          aria-label="Toggle Navigation Menu"
        >
          {isMobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shadow-xs">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-slate-900 text-base">
                ResQ
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                Disaster &amp; Relief Command
              </span>
            </div>
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5 font-medium">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Emergency Operations Center
            </div>
          </div>
        </div>

        <div className="h-6 w-px bg-slate-200 hidden md:block" />

        {/* Active Scenario Selector */}
        <div className="hidden lg:flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-xs text-slate-600 font-medium">Incident Region:</span>
          <div className="relative">
            <select
              value={network?.network_id || ""}
              onChange={handlePresetChange}
              disabled={isLoading}
              className="bg-slate-50 hover:bg-slate-100 text-xs font-medium text-slate-800 border border-slate-300 rounded-lg py-1.5 pl-2.5 pr-8 appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
            >
              <option value="__demo__">Metro River Flood (Demo)</option>
              {presets.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.title}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-500 absolute right-2.5 top-2.5 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Right Action Tools & User Status */}
      <div className="flex items-center gap-2.5">
        {/* Demo Walkthrough Modal */}
        <button
          onClick={openPresentation}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-xs transition-colors"
          title="Open Step-by-Step Guided Presentation Walkthrough"
        >
          <GraduationCap className="w-3.5 h-3.5 text-blue-600" />
          <span className="hidden md:inline">Demo Walkthrough</span>
        </button>

        {/* Lexicon / Concepts Guide */}
        <button
          onClick={openLexicon}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-xs transition-colors"
          title="Open Disaster Evacuation Lexicon & Concepts Reference"
        >
          <BookOpen className="w-3.5 h-3.5 text-blue-600" />
          <span className="hidden sm:inline">Reference Guide</span>
        </button>

        {/* Quick Solve Action */}
        <button
          onClick={() => runFullAnalysis()}
          disabled={isLoading}
          className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-xs ${
            analysis
              ? "bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200"
              : "bg-blue-600 hover:bg-blue-700 text-white"
          }`}
          title="Run Dinic's Maximum Flow and Min-Cut extraction"
        >
          {analysis ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Solved: {analysis.dinic.max_flow.toLocaleString()} /hr</span>
            </>
          ) : (
            <>
              <Radio className="w-3.5 h-3.5" />
              <span>Run Optimization</span>
            </>
          )}
        </button>

        {/* Analysis Status Pill */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg border bg-slate-50 border-slate-200 text-slate-600">
          <Activity className="w-3 h-3 text-slate-500" />
          <span className="text-slate-500">Analysis:</span>
          {analysis ? (
            <span className="text-emerald-700 font-semibold flex items-center gap-1">
              Live
            </span>
          ) : (
            <span className="text-amber-700 font-medium flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> Pending
            </span>
          )}
        </div>

        {/* User Identity / Role Badge */}
        {user ? (
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-900">
                {user.name}
              </div>
              <div className="text-[10px] text-blue-600 font-mono font-medium tracking-wide">
                {user.callsign} ({user.role.toUpperCase()})
              </div>
            </div>
            <button
              onClick={logout}
              title="Logout / Return to Landing"
              className="p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-slate-600 font-medium bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
            <UserCheck className="w-4 h-4 text-emerald-600" />
            <span className="hidden sm:inline">Guest Operator</span>
          </div>
        )}
      </div>
    </header>
  );
};
