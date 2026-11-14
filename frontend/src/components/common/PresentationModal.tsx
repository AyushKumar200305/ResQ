import React, { useState } from "react";
import { useApp } from "../../context/AppContext";
import { api } from "../../api/client";
import {
  ArrowLeft,
  ArrowRight,
  Award,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Flame,
  GitCompare,
  GraduationCap,
  Layers,
  MapPin,
  Play,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  X,
  Zap,
} from "lucide-react";

interface PresentationStep {
  stepNumber: number;
  title: string;
  subtitle: string;
  explanation: string;
  technicalNote: string;
  actionLabel: string;
  actionIcon: React.ElementType;
  pageTarget: string;
  onExecute?: (app: any) => Promise<void> | void;
}

export const PresentationModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({
  isOpen,
  onClose,
}) => {
  const app = useApp();
  const { setActivePage, runDinicAnalysis, loadPreset, addNotification } = app;
  const [currentStep, setCurrentStep] = useState(1);
  const [isExecuting, setIsExecuting] = useState(false);

  if (!isOpen) return null;

  const steps: PresentationStep[] = [
    {
      stepNumber: 1,
      title: "Step 1: View the Disaster Network",
      subtitle: "Multi-Source, Multi-Sink Urban Evacuation Grid",
      explanation:
        "ResQ models 5 hazard zones (Zones A–E with 5,500 total population), 10 transit junctions, and 4 safe regional shelters (5,100 total capacity). Notice that total demand exceeds shelter capacity, and arterial roads share critical river crossings.",
      technicalNote:
        "DAA Concept: Super-Source S* connects to all 5 affected zones with capacity = population; Super-Sink T* collects from all 4 shelters with capacity = shelter capacity.",
      actionLabel: "View Topology Canvas",
      actionIcon: MapPin,
      pageTarget: "routes",
      onExecute: async () => {
        await loadPreset("presentation_demo_dataset");
        setActivePage("routes");
        addNotification("info", "Step 1: Loaded presentation network. Explore the 5 sources and 4 shelters.");
      },
    },
    {
      stepNumber: 2,
      title: "Step 2: Run Evacuation Analysis",
      subtitle: "Dinic's Algorithm O(V² · E) Execution",
      explanation:
        "Run the core algorithmic engine. Dinic constructs a layered BFS level graph to prevent cycles, then pushes multiple augmenting flows simultaneously using DFS with pointer pruning until a blocking flow is achieved.",
      technicalNote:
        "DAA Concept: Layered level graphs ensure every augmenting path is shortest in terms of edge count. Pruned DFS guarantees blocking flow in O(V · E) per phase, with at most V phases.",
      actionLabel: "Execute Dinic Max-Flow",
      actionIcon: Zap,
      pageTarget: "algorithms",
      onExecute: async () => {
        setIsExecuting(true);
        try {
          await runDinicAnalysis();
          setActivePage("algorithms");
          addNotification("success", "Step 2: Dinic max-flow executed successfully.");
        } finally {
          setIsExecuting(false);
        }
      },
    },
    {
      stepNumber: 3,
      title: "Step 3: Understand Maximum-Flow Result",
      subtitle: "Optimal Throughput & Route Decomposition",
      explanation:
        "The algorithm achieves an optimal evacuation throughput of 4,350 people/hour. Flow decomposition transforms total edge flows into distinct turn-by-turn routes from each hazard zone to safe shelters with travel time estimates.",
      technicalNote:
        "DAA Concept: By Flow Conservation, total flow leaving sources equals total flow entering safe shelters. 79.1% of the hazard population is cleared in Wave 1.",
      actionLabel: "Inspect Corridor Flows & Routes",
      actionIcon: Layers,
      pageTarget: "algorithms",
      onExecute: () => {
        setActivePage("algorithms");
      },
    },
    {
      stepNumber: 4,
      title: "Step 4: Identify Bottlenecks (Min-Cut)",
      subtitle: "Max-Flow Min-Cut Theorem Verification",
      explanation:
        "Extract the minimum cut partition (S*, T*) via residual BFS reachability. The cut capacity exactly equals 4,350 p/h, proving mathematical optimality. 4 critical road bottlenecks and 1 saturated shelter (S3 Regional Complex) bound the system.",
      technicalNote:
        "DAA Theorem: |f*| = c(S*, T*). Only widening roads or shelters in the minimum cut can increase evacuation flow. Expanding non-cut roads has zero return on investment.",
      actionLabel: "Analyze Min-Cut Partition",
      actionIcon: ShieldAlert,
      pageTarget: "algorithms",
      onExecute: () => {
        setActivePage("algorithms");
      },
    },
    {
      stepNumber: 5,
      title: "Step 5: Simulate Disaster Road Closure",
      subtitle: "Isolated What-If Failure Injection",
      explanation:
        "What happens if North Ridgeway Bridge (R_J1_J6) collapses under flood waters? ResQ clones the network in an independent graph copy, sets its capacity to 0, and recalculates the maximum flow and shifting bottlenecks.",
      technicalNote:
        "DAA Concept: Graph cloning prevents state corruption. Dinic reroutes flow dynamically through remaining open paths (e.g. via Riverfront Overpass R_J2_J6 and Metro River Bridge).",
      actionLabel: "Simulate Bridge Failure",
      actionIcon: Flame,
      pageTarget: "algorithms",
      onExecute: async () => {
        setIsExecuting(true);
        try {
          await api.runRoadClosureScenario("R_J1_J6", "Scenario 2: North Ridgeway Bridge Failure");
          setActivePage("algorithms");
          addNotification("warning", "Step 5: Bridge R_J1_J6 severed in an isolated graph copy.");
        } finally {
          setIsExecuting(false);
        }
      },
    },
    {
      stepNumber: 6,
      title: "Step 6: Compare Changed Results",
      subtitle: "Delta Matrix & Degraded State Diagnostics",
      explanation:
        "Directly compare the baseline (4,350 p/h) against the degraded state (3,600 p/h). The bridge collapse causes a net drop of -750 evacuees/hour (-17.2%), leaving an additional 750 civilians stranded in hazard zones during hour 1.",
      technicalNote:
        "DAA Concept: Sensitivity Analysis demonstrates how structural edge failures propagate through downstream corridors and alter cut composition.",
      actionLabel: "View Scenario Comparison Matrix",
      actionIcon: GitCompare,
      pageTarget: "algorithms",
      onExecute: () => {
        setActivePage("algorithms");
      },
    },
    {
      stepNumber: 7,
      title: "Step 7: Generate Final Report & Audit",
      subtitle: "Formal PDF Situation Briefing & Viva Ready",
      explanation:
        "Generate a publication-quality PDF Situation Report compiling the network topology, algorithm metrics, min-cut bottlenecks, scenario comparison, and civil defense dispatch advisories for your college professor.",
      technicalNote:
        "DAA Defense: The report documents asymptotic complexity O(V² E), proof of theorem |f*| = c(S*, T*), and why Greedy heuristics fail on disaster graphs.",
      actionLabel: "Download Formal PDF Report",
      actionIcon: Download,
      pageTarget: "overview",
      onExecute: async () => {
        setIsExecuting(true);
        try {
          await api.downloadFile("/api/reports/pdf", "ResQ-College-Demonstration-Report.pdf");
          setActivePage("overview");
          addNotification("success", "Step 7: Official PDF Situation Report downloaded successfully!");
        } finally {
          setIsExecuting(false);
        }
      },
    },
  ];

  const active = steps[currentStep - 1];

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleExecuteAction = async () => {
    if (active.onExecute) {
      await active.onExecute(app);
    } else {
      setActivePage(active.pageTarget);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh] font-sans">
        {/* Modal Top Bar */}
        <div className="bg-slate-50 p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 shadow-xs">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>Guided Presentation Workflow</span>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  Demo Walkthrough
                </span>
              </h2>
              <p className="text-[11px] text-slate-500 font-medium">
                Step-by-step demonstration walkthrough highlighting core capabilities.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Stepper Progress Bar */}
        <div className="bg-white px-6 py-3 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-1.5 flex-1 max-w-md">
            {steps.map((s) => (
              <div
                key={s.stepNumber}
                onClick={() => setCurrentStep(s.stepNumber)}
                className={`h-2 flex-1 rounded-full cursor-pointer transition-all ${
                  s.stepNumber === currentStep
                    ? "bg-blue-600 shadow-xs"
                    : s.stepNumber < currentStep
                    ? "bg-emerald-500"
                    : "bg-slate-100 hover:bg-slate-200"
                }`}
                title={`Jump to Step ${s.stepNumber}: ${s.title}`}
              />
            ))}
          </div>

          <span className="text-xs font-mono font-bold text-blue-700 ml-4">
            Step {currentStep} of {steps.length}
          </span>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1 bg-white">
          <div>
            <span className="text-xs font-mono font-bold text-blue-600 uppercase tracking-wider block">
              {active.subtitle}
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-0.5">{active.title}</h3>
          </div>

          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed space-y-2">
            <p>{active.explanation}</p>
          </div>

          <div className="bg-blue-50/70 p-4 rounded-xl border border-blue-100 text-xs text-slate-700 flex items-start gap-2.5">
            <Award className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-blue-900 mb-0.5 font-bold">Key Takeaway:</strong>
              <span>{active.technicalNote}</span>
            </div>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="bg-slate-50 p-4 border-t border-slate-100 flex items-center justify-between gap-3">
          <button
            onClick={handlePrev}
            disabled={currentStep === 1}
            className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 flex items-center gap-1.5 transition-colors disabled:opacity-30 shadow-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Previous</span>
          </button>

          {/* Action Trigger Button */}
          <button
            onClick={handleExecuteAction}
            disabled={isExecuting}
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs flex items-center gap-2 transition-all disabled:opacity-50"
          >
            <active.actionIcon className={`w-4 h-4 ${isExecuting ? "animate-spin" : ""}`} />
            <span>{isExecuting ? "Executing..." : active.actionLabel}</span>
          </button>

          {currentStep < steps.length ? (
            <button
              onClick={handleNext}
              className="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 flex items-center gap-1.5 transition-colors shadow-xs"
            >
              <span>Next</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center gap-1.5 transition-colors shadow-xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Complete Tour</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
