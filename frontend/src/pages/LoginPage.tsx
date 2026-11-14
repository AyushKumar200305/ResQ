import React, { useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  GraduationCap,
  Info,
  KeyRound,
  Lock,
  Mail,
  Shield,
  ShieldAlert,
  Sparkles,
  Truck,
  User,
  UserCheck,
} from "lucide-react";
import { useApp } from "../context/AppContext";
import type { UserRole } from "../types/api";

interface DemoAccount {
  role: UserRole;
  title: string;
  email: string;
  password: string;
  callsign: string;
  name: string;
  badge: string;
  badgeColor: string;
  desc: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    role: "commander",
    title: "Incident Commander",
    email: "commander@resq.edu",
    password: "resq2026",
    callsign: "CMD-ALPHA",
    name: "Commander Sarah Jenkins",
    badge: "OPERATIONS",
    badgeColor: "bg-red-50 text-red-700 border-red-200",
    desc: "Full operational authority over regional evacuation routing and scenario dispatch.",
  },
  {
    role: "coordinator",
    title: "Disaster Coordinator",
    email: "coordinator@resq.edu",
    password: "coord2026",
    callsign: "COORD-01",
    name: "Elena Rostova",
    badge: "COORDINATION",
    badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
    desc: "Oversee shelter intake, regional triage priority, and inter-agency relief logistics.",
  },
  {
    role: "coordinator",
    title: "Relief Logistics Officer",
    email: "logistics@resq.edu",
    password: "transit2026",
    callsign: "LOG-01",
    name: "Officer Marcus Vance",
    badge: "LOGISTICS",
    badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
    desc: "Monitor corridor bottlenecks, travel times, camp supplies, and fair resource rationing.",
  },
];

export const LoginPage: React.FC = () => {
  const { login, setActivePage, addNotification } = useApp();
  const [activeTab, setActiveTab] = useState<"guest" | "demo">("guest");

  // Demo Login form state
  const [email, setEmail] = useState<string>("commander@resq.edu");
  const [password, setPassword] = useState<string>("resq2026");
  const [selectedRole, setSelectedRole] = useState<UserRole>("commander");
  const [name, setName] = useState<string>("Commander Sarah Jenkins");
  const [callsign, setCallsign] = useState<string>("CMD-ALPHA");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleGuestEntry = (role: UserRole = "guest", customName = "Emergency Operator (Guest)", call = "GUEST-01") => {
    login(customName, role, call);
    addNotification("info", `Entered ResQ as ${customName} [Guest Session].`);
  };

  const handleFillAccount = (acc: DemoAccount) => {
    setEmail(acc.email);
    setPassword(acc.password);
    setSelectedRole(acc.role);
    setName(acc.name);
    setCallsign(acc.callsign);
    setErrorMsg(null);
  };

  const handleDemoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Validate against known demo accounts
    const match = DEMO_ACCOUNTS.find(
      (a) => a.email.toLowerCase() === email.toLowerCase() && a.password === password
    );

    if (match) {
      login(match.name, match.role, match.callsign);
      addNotification("success", `Demo Login Verified: Welcome ${match.name}!`);
    } else if (email && password) {
      // Allow custom demo credentials gracefully with default role
      login(name || "Incident Officer", selectedRole, callsign || "CMD-01");
      addNotification("success", `Authenticated as ${name} [${selectedRole}].`);
    } else {
      setErrorMsg("Please provide both an email and password, or use 1-click Quick Fill.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-slate-900 selection:bg-blue-500 selection:text-white font-sans">
      <div className="max-w-xl w-full bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-card relative overflow-hidden">
        {/* Top Accent Line */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-600 via-sky-500 to-emerald-500" />

        {/* Top Header */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 shrink-0 shadow-xs">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                Emergency Command Access
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                ResQ Disaster Evacuation &amp; Relief Management System
              </p>
            </div>
          </div>

          <button
            onClick={() => setActivePage("landing")}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 transition-colors font-medium"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Landing</span>
          </button>
        </div>

        {/* Demonstration Notice */}
        <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl flex items-start gap-2.5 mb-6 text-xs text-slate-700">
          <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
          <div>
            <strong className="text-blue-900">Demonstration Access Notice: </strong>
            Authentication is simulated for role dispatch workflows. Choose{" "}
            <strong className="text-slate-900">Continue as Guest</strong> for immediate one-click entry, or use the{" "}
            <strong className="text-slate-900">Demo Login</strong> with pre-configured operational roles.
          </div>
        </div>

        {/* Mode Selector Tabs */}
        <div className="grid grid-cols-2 p-1 bg-slate-100 rounded-xl border border-slate-200 mb-6 shadow-xs">
          <button
            type="button"
            onClick={() => setActiveTab("guest")}
            className={`py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "guest"
                ? "bg-white text-blue-700 shadow-xs border border-slate-200/60"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Continue as Guest</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("demo")}
            className={`py-2 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              activeTab === "demo"
                ? "bg-white text-blue-700 shadow-xs border border-slate-200/60"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <KeyRound className="w-3.5 h-3.5 text-blue-600" />
            <span>Optional Demo Login</span>
          </button>
        </div>

        {/* Tab 1: Guest Access */}
        {activeTab === "guest" && (
          <div className="space-y-4">
            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              Select an operational role to enter ResQ instantly with no password required:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.role}
                  type="button"
                  onClick={() => handleGuestEntry(acc.role, acc.name, acc.callsign)}
                  className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-white hover:border-blue-400 text-left transition-all group shadow-xs hover:shadow-cardHover"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${acc.badgeColor}`}>
                      {acc.badge}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition-colors" />
                  </div>
                  <div className="text-xs font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                    {acc.title}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                    {acc.desc}
                  </div>
                </button>
              ))}

              {/* Public Observer */}
              <button
                type="button"
                onClick={() => handleGuestEntry("guest", "Public Safety Observer", "OBS-01")}
                className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-white hover:border-blue-400 text-left transition-all group shadow-xs hover:shadow-cardHover"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border bg-slate-100 text-slate-700 border-slate-200">
                    OBSERVER
                  </span>
                  <ArrowRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-blue-600 transition-colors" />
                </div>
                <div className="text-xs font-bold text-slate-900 group-hover:text-blue-700 transition-colors">
                  Public Safety Observer
                </div>
                <div className="text-[10px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                  General viewing access to disaster situation telemetry and simulation reports.
                </div>
              </button>
            </div>

            <div className="pt-3">
              <button
                type="button"
                onClick={() => handleGuestEntry("commander", "Emergency Operations Guest", "CMD-GUEST")}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-xs transition-all"
              >
                <span>Enter ResQ Command Center (1-Click Guest)</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: Demo Login */}
        {activeTab === "demo" && (
          <form onSubmit={handleDemoSubmit} className="space-y-4">
            {/* Quick-fill Pills */}
            <div>
              <label className="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                Quick Fill Demo Credentials:
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {DEMO_ACCOUNTS.map((acc) => (
                  <button
                    key={acc.role}
                    type="button"
                    onClick={() => handleFillAccount(acc)}
                    className={`px-3 py-2 rounded-xl border text-left transition-all shadow-xs ${
                      email.toLowerCase() === acc.email.toLowerCase()
                        ? "bg-blue-50 border-blue-400 text-blue-950 font-bold"
                        : "bg-slate-50 border-slate-200 text-slate-600 hover:border-slate-300"
                    }`}
                  >
                    <div className="text-[11px] font-bold text-slate-900 truncate">
                      {acc.title.split("/")[0]}
                    </div>
                    <div className="text-[9px] font-mono text-slate-500 truncate">
                      {acc.password}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700 font-medium">
                {errorMsg}
              </div>
            )}

            {/* Email Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Demo Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  placeholder="e.g. evaluator@resq.edu"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                />
              </div>
            </div>

            {/* Password Input */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Demo Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="e.g. daa2026"
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
                />
              </div>
            </div>

            {/* Credential Reference Table */}
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 text-[10px] font-mono text-slate-600 space-y-1 shadow-xs">
              <div className="text-slate-900 font-sans font-bold mb-1">
                Documented Demo Credentials:
              </div>
              <div className="flex justify-between">
                <span>Evaluator: evaluator@resq.edu</span>
                <span className="text-blue-700 font-bold">daa2026</span>
              </div>
              <div className="flex justify-between">
                <span>Commander: commander@resq.edu</span>
                <span className="text-blue-700 font-bold">resq2026</span>
              </div>
              <div className="flex justify-between">
                <span>Logistics: logistics@resq.edu</span>
                <span className="text-blue-700 font-bold">transit2026</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => handleGuestEntry("guest")}
                className="text-xs text-slate-500 hover:text-slate-800 transition-colors font-medium"
              >
                Skip to Guest Mode
              </button>
              <button
                type="submit"
                className="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-xs transition-all"
              >
                <span>Authenticate &amp; Enter</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
