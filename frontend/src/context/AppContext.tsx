import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";
import type {
  DijkstraData,
  DinicData,
  FullAnalysisData,
  GreedyCompareData,
  MinCutData,
  NetworkData,
  PresetSummary,
  ReliefOverviewData,
  ScenarioEvaluationData,
  UserRole,
  UserSession,
} from "../types/api";

export interface Notification {
  type: "success" | "info" | "warning" | "error";
  message: string;
}

interface AppContextType {
  user: UserSession | null;
  activePage: string;
  network: NetworkData | null;
  analysis: FullAnalysisData | null;
  dinicResult: DinicData | null;
  minCutResult: MinCutData | null;
  dijkstraResult: DijkstraData | null;
  scenarios: ScenarioEvaluationData[];
  comparison: GreedyCompareData | null;
  presets: PresetSummary[];
  reliefOverview: ReliefOverviewData | null;
  isReliefLoading: boolean;
  isLoading: boolean;
  isSolving: boolean;
  loadingMessage: string;
  error: string | null;
  notification: Notification | null;
  isPresentationOpen: boolean;
  isLexiconOpen: boolean;
  isSidebarCollapsed: boolean;
  isMobileNavOpen: boolean;
  // Actions
  login: (name: string, role: UserRole, callsign: string) => void;
  logout: () => void;
  setActivePage: (page: string) => void;
  toggleSidebarCollapse: () => void;
  toggleMobileNav: () => void;
  closeMobileNav: () => void;
  openPresentation: () => void;
  closePresentation: () => void;
  openLexicon: () => void;
  closeLexicon: () => void;
  setDijkstraResult: (d: DijkstraData | null) => void;
  refreshNetwork: () => Promise<void>;
  refreshRelief: () => Promise<void>;
  loadPreset: (key: string) => Promise<void>;
  switchPreset: (key: string) => Promise<void>;
  loadDemo: () => Promise<void>;
  runFullAnalysis: (waveHours?: number, upgradeDelta?: number) => Promise<void>;
  runDinicAnalysis: (waveHours?: number, upgradeDelta?: number) => Promise<void>;
  runAllScenarios: () => Promise<void>;
  notify: (type: Notification["type"], message: string) => void;
  addNotification: (type: Notification["type"], message: string) => void;
  clearNotification: () => void;
  clearError: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(() => {
    const saved = localStorage.getItem("resq_user");
    return saved ? JSON.parse(saved) : null;
  });

  // URL Hash routing: enables direct URLs, page refresh, and back/forward navigation
  const [activePage, setActivePageState] = useState<string>(() => {
    if (typeof window !== "undefined" && window.location.hash) {
      const pageFromHash = window.location.hash.replace(/^#\/?/, "");
      if (pageFromHash) return pageFromHash;
    }
    return localStorage.getItem("resq_user") ? "overview" : "landing";
  });

  const setActivePage = (page: string) => {
    setActivePageState(page);
    setIsMobileNavOpen(false); // Close mobile drawer when navigating
    if (typeof window !== "undefined") {
      window.location.hash = `#/${page}`;
    }
  };

  useEffect(() => {
    const handleHashChange = () => {
      const pageFromHash = window.location.hash.replace(/^#\/?/, "");
      if (pageFromHash) {
        setActivePageState(pageFromHash);
      }
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(() => {
    return localStorage.getItem("resq_sidebar_collapsed") === "true";
  });
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

  const toggleSidebarCollapse = () => {
    setIsSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("resq_sidebar_collapsed", String(next));
      return next;
    });
  };

  const toggleMobileNav = () => setIsMobileNavOpen((prev) => !prev);
  const closeMobileNav = () => setIsMobileNavOpen(false);

  const [network, setNetwork] = useState<NetworkData | null>(null);
  const [analysis, setAnalysis] = useState<FullAnalysisData | null>(null);
  const [dijkstraResult, setDijkstraResult] = useState<DijkstraData | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioEvaluationData[]>([]);
  const [comparison, setComparison] = useState<GreedyCompareData | null>(null);
  const [presets, setPresets] = useState<PresetSummary[]>([]);
  const [reliefOverview, setReliefOverview] = useState<ReliefOverviewData | null>(null);
  const [isReliefLoading, setIsReliefLoading] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingMessage, setLoadingMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<Notification | null>(null);
  const [isPresentationOpen, setIsPresentationOpen] = useState<boolean>(false);
  const [isLexiconOpen, setIsLexiconOpen] = useState<boolean>(false);

  // Initialize network and presets on startup
  useEffect(() => {
    async function init() {
      try {
        setIsLoading(true);
        setLoadingMessage("Connecting to ResQ Emergency Backend...");
        const [netData, presetList] = await Promise.all([
          api.getCurrentNetwork(),
          api.getPresets(),
        ]);
        setNetwork(netData);
        setPresets(presetList);
        
        // Also precompute baseline analysis and relief overview so users have immediate telemetry
        try {
          const [initAnalysis, initRelief] = await Promise.allSettled([
            api.runFullAnalysis(8, 100),
            api.getReliefOverview(),
          ]);
          if (initAnalysis.status === "fulfilled") setAnalysis(initAnalysis.value);
          if (initRelief.status === "fulfilled") setReliefOverview(initRelief.value);
        } catch {
          // If initial solve fails, user can run manually
        }
      } catch (err: unknown) {
        console.error("Initialization error:", err);
        setError(`Unable to connect to FastAPI backend at ${api.getBaseUrl()}. Please ensure the server is running.`);
      } finally {
        setIsLoading(false);
        setLoadingMessage("");
      }
    }
    init();
  }, []);

  const login = (name: string, role: UserRole, callsign: string) => {
    const session: UserSession = {
      name,
      role,
      callsign: callsign || "CMD-ALPHA",
      enteredAt: new Date().toLocaleTimeString(),
    };
    setUser(session);
    localStorage.setItem("resq_user", JSON.stringify(session));
    setActivePage("overview");
    notify("success", `Operational access granted: Welcome ${name} [${session.callsign}]`);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("resq_user");
    setActivePage("landing");
    notify("info", "Session terminated. Safe return to command center.");
  };

  const refreshNetwork = async () => {
    try {
      setIsLoading(true);
      setLoadingMessage("Fetching latest network state...");
      const updated = await api.getCurrentNetwork();
      setNetwork(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to refresh network");
    } finally {
      setIsLoading(false);
      setLoadingMessage("");
    }
  };

  const refreshRelief = async () => {
    try {
      setIsReliefLoading(true);
      const data = await api.getReliefOverview();
      setReliefOverview(data);
    } catch (err: unknown) {
      console.warn("Could not refresh relief overview:", err);
    } finally {
      setIsReliefLoading(false);
    }
  };

  const loadPreset = async (key: string) => {
    try {
      setIsLoading(true);
      setLoadingMessage(`Loading disaster preset [${key}]...`);
      const updated = await api.loadPreset(key);
      setNetwork(updated);
      setAnalysis(null);
      setDijkstraResult(null);
      setScenarios([]);
      setComparison(null);
      
      // Auto run analysis and relief overview on loaded preset
      try {
        const [solved, relief] = await Promise.allSettled([
          api.runFullAnalysis(8, 100),
          api.getReliefOverview(),
        ]);
        if (solved.status === "fulfilled") setAnalysis(solved.value);
        if (relief.status === "fulfilled") setReliefOverview(relief.value);
      } catch {
        // user can solve manually
      }

      notify("success", `Loaded preset: ${updated.name}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load preset");
    } finally {
      setIsLoading(false);
      setLoadingMessage("");
    }
  };

  const switchPreset = loadPreset;

  const loadDemo = async () => {
    try {
      setIsLoading(true);
      setLoadingMessage("Restoring official demo dataset...");
      const updated = await api.loadDemoNetwork();
      setNetwork(updated);
      setAnalysis(null);
      setDijkstraResult(null);
      setScenarios([]);
      setComparison(null);

      try {
        const [solved, relief] = await Promise.allSettled([
          api.runFullAnalysis(8, 100),
          api.getReliefOverview(),
        ]);
        if (solved.status === "fulfilled") setAnalysis(solved.value);
        if (relief.status === "fulfilled") setReliefOverview(relief.value);
      } catch {
        // user can solve manually
      }

      notify("success", "Demo network restored: Metro River Basin Flood");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load demo");
    } finally {
      setIsLoading(false);
      setLoadingMessage("");
    }
  };

  const runFullAnalysis = async (waveHours = 8, upgradeDelta = 100) => {
    try {
      setIsLoading(true);
      setLoadingMessage("Executing Dinic Max-Flow and Min-Cut extraction...");
      const result = await api.runFullAnalysis(waveHours, upgradeDelta);
      setAnalysis(result);
      notify(
        "success",
        `Optimization complete: Max Evacuation Flow = ${result.dinic.max_flow.toLocaleString()} people/hour`
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run analysis");
    } finally {
      setIsLoading(false);
      setLoadingMessage("");
    }
  };

  const runDinicAnalysis = runFullAnalysis;

  const runAllScenarios = async () => {
    try {
      setIsLoading(true);
      setLoadingMessage("Evaluating Scenarios 1–5 across independent network copies...");
      const res = await api.runAllScenarios();
      setScenarios(res.scenarios);
      notify("success", `Completed What-If analysis across ${res.scenarios.length} scenarios.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run scenarios");
    } finally {
      setIsLoading(false);
      setLoadingMessage("");
    }
  };

  const notify = (type: Notification["type"], message: string) => {
    setNotification({ type, message });
    setTimeout(() => {
      setNotification((curr) => (curr?.message === message ? null : curr));
    }, 5000);
  };

  const addNotification = notify;
  const clearNotification = () => setNotification(null);
  const clearError = () => setError(null);

  const dinicResult = analysis?.dinic || null;
  const minCutResult = analysis?.min_cut || null;

  return (
    <AppContext.Provider
      value={{
        user,
        activePage,
        network,
        analysis,
        dinicResult,
        minCutResult,
        dijkstraResult,
        scenarios,
        comparison,
        presets,
        reliefOverview,
        isReliefLoading,
        isLoading,
        isSolving: isLoading,
        loadingMessage,
        error,
        notification,
        isPresentationOpen,
        openPresentation: () => setIsPresentationOpen(true),
        closePresentation: () => setIsPresentationOpen(false),
        isLexiconOpen,
        openLexicon: () => setIsLexiconOpen(true),
        closeLexicon: () => setIsLexiconOpen(false),
        isSidebarCollapsed,
        toggleSidebarCollapse,
        isMobileNavOpen,
        toggleMobileNav,
        closeMobileNav,
        login,
        logout,
        setActivePage,
        setDijkstraResult,
        refreshNetwork,
        refreshRelief,
        loadPreset,
        switchPreset,
        loadDemo,
        runFullAnalysis,
        runDinicAnalysis,
        runAllScenarios,
        notify,
        addNotification,
        clearNotification,
        clearError,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};
