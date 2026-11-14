import React from "react";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Boxes,
  Compass,
  FileText,
  FlaskConical,
  Info,
  LayoutDashboard,
  PanelLeftClose,
  PanelLeftOpen,
  PencilRuler,
  PlayCircle,
  Route,
  Scale,
  ShieldCheck,
  X,
} from "lucide-react";
import { useApp } from "../../context/AppContext";

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  description: string;
  badge?: string;
  badgeColor?: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const {
    activePage,
    setActivePage,
    reliefOverview,
    analysis,
    isSidebarCollapsed,
    toggleSidebarCollapse,
    isMobileNavOpen,
    closeMobileNav,
  } = useApp();

  const groups: NavGroup[] = [
    {
      title: "Operations & Relief",
      items: [
        {
          id: "overview",
          label: "Situation Overview",
          icon: LayoutDashboard,
          description: "Critical areas, actions, warnings, and shortages",
          badge: reliefOverview ? "Live" : undefined,
          badgeColor: "bg-emerald-50 text-emerald-700 border-emerald-200",
        },
        {
          id: "priorities",
          label: "Evacuation Priorities",
          icon: AlertOctagon,
          description: "Affected areas ranked by urgency with explainable reasons",
          badge: reliefOverview?.priorities ? `${reliefOverview.priorities.length} Areas` : undefined,
          badgeColor: "bg-rose-50 text-rose-700 border-rose-200",
        },
        {
          id: "routes",
          label: "Routes & Shelters",
          icon: Compass,
          description: "Interactive evacuation map, routes, and shelter destinations",
          badge: reliefOverview?.routes ? `${reliefOverview.routes.length} Corridors` : undefined,
          badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
        },
        {
          id: "resources",
          label: "Camp Resources",
          icon: Boxes,
          description: "Shelter intake, water/food demand, stock, and fair allocation",
          badge: reliefOverview?.shelters ? `${reliefOverview.shelters.length} Camps` : undefined,
          badgeColor: "bg-amber-50 text-amber-800 border-amber-200",
        },
      ],
    },
    {
      title: "DAA Algorithms & Analysis",
      items: [
        {
          id: "builder",
          label: "Network Builder",
          icon: PencilRuler,
          description: "Interactive graph editor, capacities & JSON import/export",
        },
        {
          id: "simulation",
          label: "Live Simulation",
          icon: PlayCircle,
          description: "Step-by-step playback scrubber & multi-hour wave progression",
        },
        {
          id: "flow",
          label: "Flow Analysis",
          icon: Activity,
          description: "Road-by-road flow utilization, residual capacity & saturation",
          badge: analysis ? `${analysis.dinic.max_flow.toLocaleString()} p/h` : undefined,
          badgeColor: "bg-indigo-50 text-indigo-700 border-indigo-200",
        },
        {
          id: "bottlenecks",
          label: "Bottleneck Analysis",
          icon: AlertTriangle,
          description: "Min-Cut (S*, T*) reachability & saturated cut chokepoints",
          badge: analysis?.min_cut ? `${analysis.min_cut.road_bottlenecks.length} Cuts` : undefined,
          badgeColor: "bg-rose-50 text-rose-700 border-rose-200",
        },
        {
          id: "scenarios",
          label: "Scenario Lab",
          icon: FlaskConical,
          description: "Disaster failure injection: road closures & shelter shifts",
          badge: "5 Tests",
          badgeColor: "bg-blue-50 text-blue-700 border-blue-200",
        },
        {
          id: "compare",
          label: "Algorithm Comparison",
          icon: Scale,
          description: "Dinic optimal vs. Greedy baselines (Shortest-Hop, Widest, DFS)",
        },
        {
          id: "dijkstra",
          label: "Shortest Path (Dijkstra)",
          icon: Route,
          description: "Point-to-point shortest route vs. alternative detours",
        },
      ],
    },
    {
      title: "System & Reporting",
      items: [
        {
          id: "reports",
          label: "Reports & Audit",
          icon: FileText,
          description: "Download publication-ready PDF, JSON, and CSV audits",
        },
        {
          id: "about",
          label: "About ResQ",
          icon: Info,
          description: "DAA asymptotic complexity O(V²E), theorem proofs & team",
        },
      ],
    },
  ];

  // Render navigation item button
  const renderNavButton = (item: NavItem, isCollapsed: boolean) => {
    const Icon = item.icon;
    const isActive = activePage === item.id;

    return (
      <button
        key={item.id}
        onClick={() => {
          setActivePage(item.id);
          closeMobileNav();
        }}
        title={`${item.label} — ${item.description}`}
        className={`w-full group flex items-center ${
          isCollapsed ? "justify-center px-2 py-2.5" : "justify-between py-2 px-2.5"
        } rounded-xl text-left text-xs transition-all ${
          isActive
            ? "bg-blue-50/90 text-blue-700 font-semibold border-l-4 border-l-blue-600 shadow-xs"
            : "text-slate-600 hover:text-slate-900 hover:bg-slate-50 border-l-4 border-l-transparent font-medium"
        }`}
      >
        <div className={`flex items-center ${isCollapsed ? "justify-center" : "gap-2.5"} min-w-0`}>
          <Icon
            className={`w-4 h-4 shrink-0 transition-colors ${
              isActive ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"
            }`}
          />
          {!isCollapsed && <span className="truncate">{item.label}</span>}
        </div>
        {!isCollapsed && item.badge && (
          <span
            className={`text-[10px] px-2 py-0.5 rounded-full border font-mono font-medium shrink-0 ml-1.5 ${
              item.badgeColor || "bg-slate-100 text-slate-700 border-slate-200"
            }`}
          >
            {item.badge}
          </span>
        )}
      </button>
    );
  };

  // Nav list content
  const renderNavContent = (isCollapsed: boolean) => (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-5">
      {groups.map((group) => (
        <div key={group.title} className="space-y-1">
          {!isCollapsed ? (
            <div className="px-2.5 py-1 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
              {group.title}
            </div>
          ) : (
            <div className="h-px bg-slate-200 my-2 mx-1" />
          )}
          <div className="space-y-0.5">
            {group.items.map((item) => renderNavButton(item, isCollapsed))}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Collapsible) */}
      <aside
        className={`hidden md:flex flex-col justify-between bg-white border-r border-slate-200 select-none shrink-0 min-h-[calc(100vh-4rem)] shadow-xs transition-all duration-200 ${
          isSidebarCollapsed ? "w-16" : "w-64"
        }`}
      >
        {renderNavContent(isSidebarCollapsed)}

        {/* Footer Collapse Toggle & Operational Note */}
        <div className="p-3 border-t border-slate-200/80 bg-white space-y-2">
          {!isSidebarCollapsed && (
            <div className="p-2.5 border border-slate-200 bg-slate-50/80 rounded-xl">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                <span className="truncate">Decision Verification</span>
              </div>
              <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">
                Dinic Max Flow, Min-Cut &amp; Sphere standards verified.
              </p>
            </div>
          )}

          <button
            onClick={toggleSidebarCollapse}
            className={`w-full flex items-center ${
              isSidebarCollapsed ? "justify-center p-2" : "justify-between px-3 py-2"
            } text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 rounded-lg border border-slate-200/70 transition-colors shadow-xs`}
            title={isSidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            <div className="flex items-center gap-2">
              {isSidebarCollapsed ? (
                <PanelLeftOpen className="w-4 h-4 text-blue-600" />
              ) : (
                <>
                  <PanelLeftClose className="w-4 h-4 text-slate-500" />
                  <span>Collapse Menu</span>
                </>
              )}
            </div>
          </button>
        </div>
      </aside>

      {/* Mobile Drawer (Visible when isMobileNavOpen is true) */}
      {isMobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
            onClick={closeMobileNav}
          />

          {/* Drawer Panel */}
          <div className="relative w-72 max-w-[85vw] bg-white h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-left duration-200">
            {/* Drawer Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Operations Navigation
              </span>
              <button
                onClick={closeMobileNav}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Nav Items */}
            {renderNavContent(false)}

            {/* Drawer Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50">
              <div className="text-[11px] text-slate-500 font-medium">
                ResQ Disaster Operations v2.0
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
