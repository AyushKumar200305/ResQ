import React, { useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  Code2,
  GraduationCap,
  Scale,
  ShieldAlert,
} from "lucide-react";

interface FAQItem {
  question: string;
  answer: string;
  tag: string;
}

const VIVA_QUESTIONS: FAQItem[] = [
  {
    tag: "Complexity",
    question: "Why choose Dinic's Algorithm over Edmonds-Karp and Ford-Fulkerson?",
    answer:
      "Ford-Fulkerson runs in O(E · |f*|), which is pseudo-polynomial and slow for large capacities. Edmonds-Karp improves this to O(V E²) by finding augmenting paths via BFS. Dinic's algorithm dramatically improves efficiency to O(V² E) by constructing a BFS level graph and pushing multiple blocking flows simultaneously via DFS. Furthermore, on unit-capacity networks, Dinic achieves O(E √V), making it optimal for disaster routing.",
  },
  {
    tag: "Modeling",
    question: "How does ResQ handle multiple disaster hazard zones and multiple safe shelters?",
    answer:
      "ResQ introduces a virtual Super-Source (S*) and virtual Super-Sink (T*). Directed edges connect S* to each affected area with capacity equal to that area's evacuee population. Directed edges connect each shelter to T* with capacity equal to the shelter's intake limit. This transforms a multi-source multi-sink problem into a canonical single-source single-sink network with zero algorithmic modification.",
  },
  {
    tag: "Theory",
    question: "What is the Max-Flow Min-Cut Theorem and how is it proven in ResQ?",
    answer:
      "The Max-Flow Min-Cut Theorem states that the maximum volume of flow from source to sink equals the minimum capacity of an (s, t)-cut: |f*| = c(S*, T*). In ResQ, once Dinic terminates and no augmenting path exists in the residual network, we perform a BFS from S* in the residual graph. The set of reachable vertices forms S*, and unreachable vertices form T*. The sum of capacities of forward edges spanning S* to T* exactly equals the maximum flow.",
  },
  {
    tag: "Greedy Failure",
    question: "Why does the greedy algorithm fail on evacuation networks?",
    answer:
      "A greedy strategy augments flow along locally attractive paths (e.g., shortest hop or widest path) without creating reverse residual edges. Once capacity is committed forward, it can never be undone or rerouted. In networks with shared bottlenecks (like the 'Greedy Trap' counterexample), greedy fills a central bridge that blocks two superior independent paths, cutting achievable flow in half (1,000 vs 2,000 p/h).",
  },
  {
    tag: "Engineering",
    question: "How does flow decomposition convert total flow into driver routes?",
    answer:
      "A raw max-flow solution only provides edge flow values f(u, v). ResQ runs a cycle-canceling path decomposition algorithm that iteratively extracts simple paths from affected areas to shelters until all flow is accounted for. Each path is assigned a specific flow volume and free-flow travel time, giving civil authorities turn-by-turn routing directives.",
  },
  {
    tag: "Level Graph",
    question: "What prevents infinite cycles and redundant DFS searches in Dinic?",
    answer:
      "Dinic constructs a layered Level Graph using BFS where level[v] = level[u] + 1. The DFS only pushes flow along edges pointing to the immediate next level (level[v] == level[u] + 1). This completely eliminates backward cycles. Additionally, pointer advancement ('ptr' array) caches traversed edges so dead ends are never revisited during a phase, guaranteeing blocking flow in O(V E).",
  },
];

export const AboutPage: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const toggleQuestion = (idx: number) => {
    setOpenIndex(openIndex === idx ? null : idx);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <GraduationCap className="w-5 h-5 text-sky-600" />
            About ResQ & DAA Viva Evaluation Guide
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Comprehensive reference on algorithm design, asymptotic complexity proofs, and architectural design for academic evaluation.
          </p>
        </div>
      </div>

      {/* Hero Overview Card */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-6 shadow-xs">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2.5 rounded-xl bg-sky-50 text-sky-600 border border-sky-200">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              ResQ — Disaster Evacuation Flow & Bottleneck Analysis Optimizer
            </h2>
            <span className="text-xs font-mono font-semibold text-sky-700">
              Department of Computer Science & Engineering | Design & Analysis of Algorithms
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-600 leading-relaxed max-w-4xl">
          ResQ applies maximum network flow theory, residual graph modeling, and min-cut duality to urban disaster evacuation planning. During regional emergencies (such as urban flash floods, chemical releases, or tsunamis), thousands of civilians must reach safe shelters across constrained road networks. ResQ computes optimal non-conflicting routing vectors, pinpoints structural bottlenecks, and tests resilience against bridge and shelter failures.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5 pt-4 border-t border-slate-100 text-xs">
          <div>
            <span className="text-slate-500 block text-[11px] font-medium">Primary Algorithm</span>
            <span className="font-bold text-sky-700 font-mono">Dinic's Max Flow</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px] font-medium">Time Complexity</span>
            <span className="font-bold text-emerald-700 font-mono">O(V² · E)</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px] font-medium">Dual Theorem</span>
            <span className="font-bold text-rose-700 font-mono">Max-Flow Min-Cut</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px] font-medium">Shortest Path</span>
            <span className="font-bold text-amber-700 font-mono">Dijkstra Min-Heap</span>
          </div>
        </div>
      </div>

      {/* Algorithm Complexity Comparison Matrix */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
          <Scale className="w-4 h-4 text-sky-600" />
          Theoretical Complexity Comparison Matrix
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-[11px]">
              <tr>
                <th className="py-2.5 px-3">Algorithm</th>
                <th className="py-2.5 px-3">Paradigms / Strategy</th>
                <th className="py-2.5 px-3">General Time Complexity</th>
                <th className="py-2.5 px-3">Unit Network Bound</th>
                <th className="py-2.5 px-3 text-center">Optimality Guarantee</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="bg-sky-50/50">
                <td className="py-2.5 px-3 font-bold text-sky-700">Dinic's Algorithm (ResQ Core)</td>
                <td className="py-2.5 px-3 text-slate-800 font-sans">BFS Level Graph + DFS Blocking Flow</td>
                <td className="py-2.5 px-3 font-bold text-emerald-700">O(V² · E)</td>
                <td className="py-2.5 px-3 text-emerald-700">O(E · √V)</td>
                <td className="py-2.5 px-3 text-center text-emerald-700 font-bold">YES (Global Max)</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-slate-800 font-medium">Edmonds-Karp</td>
                <td className="py-2.5 px-3 text-slate-600 font-sans">Shortest Augmenting Path via BFS</td>
                <td className="py-2.5 px-3 text-slate-700">O(V · E²)</td>
                <td className="py-2.5 px-3 text-slate-600">O(V · E²)</td>
                <td className="py-2.5 px-3 text-center text-emerald-700 font-bold">YES</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-slate-800 font-medium">Ford-Fulkerson</td>
                <td className="py-2.5 px-3 text-slate-600 font-sans">Arbitrary Augmenting Path (DFS)</td>
                <td className="py-2.5 px-3 text-slate-700">O(E · |f*|) [Pseudo-polynomial]</td>
                <td className="py-2.5 px-3 text-slate-600">O(E · |f*|)</td>
                <td className="py-2.5 px-3 text-center text-emerald-700 font-bold">YES</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-slate-800 font-medium">Greedy Baseline</td>
                <td className="py-2.5 px-3 text-slate-600 font-sans">Locally greedy without reverse edges</td>
                <td className="py-2.5 px-3 text-slate-700">O(E · (V + E))</td>
                <td className="py-2.5 px-3 text-slate-600">O(E · (V + E))</td>
                <td className="py-2.5 px-3 text-center text-rose-600 font-bold">NO (Suboptimal)</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 text-slate-800 font-medium">Dijkstra Shortest Path</td>
                <td className="py-2.5 px-3 text-slate-600 font-sans">Binary Min-Heap Priority Queue</td>
                <td className="py-2.5 px-3 text-slate-700">O((V + E) log V)</td>
                <td className="py-2.5 px-3 text-slate-600">—</td>
                <td className="py-2.5 px-3 text-center text-sky-700 font-sans text-[11px] font-semibold">Single vehicle only</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* DAA Viva Flashcards & Examiner Q&A */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-sky-600" />
              DAA Examiner Viva Flashcards & Architectural Defense
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Click any question below to inspect rigorous DAA answers prepared for final university review.
            </p>
          </div>
        </div>

        <div className="space-y-2.5">
          {VIVA_QUESTIONS.map((item, idx) => {
            const isOpen = openIndex === idx;
            return (
              <div
                key={idx}
                className="bg-slate-50/50 border border-slate-200 rounded-xl overflow-hidden transition-all"
              >
                <button
                  onClick={() => toggleQuestion(idx)}
                  className="w-full p-3.5 text-left flex items-center justify-between gap-3 hover:bg-slate-100/60 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-sky-50 text-sky-700 border border-sky-200">
                      {item.tag}
                    </span>
                    <span className="text-xs font-semibold text-slate-800">{item.question}</span>
                  </div>
                  {isOpen ? (
                    <ChevronDown className="w-4 h-4 text-slate-500 shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                  )}
                </button>

                {isOpen && (
                  <div className="p-4 pt-0 text-xs text-slate-600 leading-relaxed border-t border-slate-200 bg-white">
                    <p>{item.answer}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Technology Stack Credits */}
      <div className="bg-white border border-slate-200/80 rounded-xl p-5 shadow-xs">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2 mb-3">
          <Code2 className="w-4 h-4 text-sky-600" />
          Technical Stack & Architectural Blueprint
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <h4 className="font-bold text-sky-700 mb-1">Frontend Layer</h4>
            <ul className="text-slate-600 space-y-1 list-disc list-inside">
              <li>React 19 + TypeScript + Vite</li>
              <li>Tailwind CSS Premium Light Theme</li>
              <li>@xyflow/react (Interactive Graph Canvas)</li>
              <li>Recharts (Analytics & Wave Charts)</li>
              <li>Lucide React (Standard Icons)</li>
            </ul>
          </div>

          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <h4 className="font-bold text-emerald-700 mb-1">Backend API Layer</h4>
            <ul className="text-slate-600 space-y-1 list-disc list-inside">
              <li>Python 3.14 + FastAPI</li>
              <li>Pydantic v2 Schema Validation</li>
              <li>Uvicorn ASGI Server</li>
              <li>Modular RESTful Endpoints</li>
              <li>ReportLab PDF Generation Engine</li>
            </ul>
          </div>

          <div className="bg-slate-50/70 p-4 rounded-xl border border-slate-200">
            <h4 className="font-bold text-amber-700 mb-1">Core Algorithm Engines</h4>
            <ul className="text-slate-600 space-y-1 list-disc list-inside">
              <li>Dinic Maximum Flow (O(V² E))</li>
              <li>Residual Cut & Bottleneck Extraction</li>
              <li>Multi-Heuristic Greedy Baseline</li>
              <li>Dijkstra Binary Min-Heap Route Finder</li>
              <li>Pytest Mathematical Validation Suite</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
