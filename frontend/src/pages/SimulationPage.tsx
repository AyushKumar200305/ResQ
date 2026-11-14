import React, { useState, useEffect, useRef } from "react";
import { useApp } from "../context/AppContext";
import { api } from "../api/client";
import type { PlaybackFrame, WaveStep } from "../types/api";
import { TermTooltip } from "../components/common/TermTooltip";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  SkipBack,
  Clock,
  Activity,
  Info,
} from "lucide-react";

export const SimulationPage: React.FC = () => {
  const { network, dinicResult, addNotification } = useApp();

  const [frames, setFrames] = useState<PlaybackFrame[]>([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1000); // ms per step
  const [waveSchedule, setWaveSchedule] = useState<WaveStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Playback timer ref using browser number ID
  const timerRef = useRef<number | null>(null);

  // Fetch playback frames and wave simulation schedule
  const loadSimulationData = async () => {
    setIsLoading(true);
    try {
      const [playbackData, waves] = await Promise.all([
        api.getPlaybackFrames(),
        api.getWaveSimulation(12),
      ]);
      setFrames(playbackData.frames);
      setWaveSchedule(waves);
      setCurrentFrameIndex(0);
      setIsPlaying(false);
    } catch (err: any) {
      addNotification("error", `Failed to load evacuation simulation: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSimulationData();
  }, [network]);

  // Handle Play/Pause timer
  useEffect(() => {
    if (isPlaying) {
      timerRef.current = window.setInterval(() => {
        setCurrentFrameIndex((prev) => {
          if (prev >= frames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, playbackSpeed);
    } else if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    return () => {
      if (timerRef.current !== null) clearInterval(timerRef.current);
    };
  }, [isPlaying, frames.length, playbackSpeed]);

  const handleStepNext = () => {
    if (currentFrameIndex < frames.length - 1) {
      setCurrentFrameIndex((p) => p + 1);
    }
  };

  const handleStepPrev = () => {
    if (currentFrameIndex > 0) {
      setCurrentFrameIndex((p) => p - 1);
    }
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(0);
  };

  const activeFrame: PlaybackFrame | undefined = frames[currentFrameIndex];
  const maxCumulativeFlow = frames.length > 0 ? frames[frames.length - 1].cumulative_flow : (dinicResult?.max_flow ?? 0);
  const currentFlow = activeFrame ? activeFrame.cumulative_flow : 0;
  const flowProgressPct = maxCumulativeFlow > 0 ? (currentFlow / maxCumulativeFlow) * 100 : 0;

  // Total population & clearance hours
  const totalPop = network?.total_population ?? 0;
  const maxHourlyFlow = dinicResult?.max_flow ?? 0;
  const clearanceHours = maxHourlyFlow > 0 ? totalPop / maxHourlyFlow : 0;

  // Chart data from evacuation schedule
  const scheduleChartData = waveSchedule.map((entry) => ({
    hour: `T+${entry.hour}h`,
    hourNum: entry.hour,
    clearedThisHour: entry.evacuated_this_hour,
    cumEvacuated: entry.cumulative_evacuated,
    stillRemaining: entry.remaining_population,
  }));

  return (
    <div className="space-y-6">
      {/* Page Title & Operational Status */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-3.5">
          <div className="p-3 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 shrink-0 mt-0.5 shadow-xs">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h1 className="text-lg font-bold text-slate-900 tracking-tight">Evacuation Simulation &amp; Wave Progression</h1>
              <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                DYNAMIC TRACE
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Deterministic step-by-step trace of Dinic's augmenting paths, corridor saturation, and multi-hour wave clearance.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadSimulationData}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold border border-slate-200 shadow-xs transition-colors"
          >
            <RotateCcw className={`w-3.5 h-3.5 text-slate-500 ${isLoading ? "animate-spin text-blue-600" : ""}`} />
            <span>Reload Sim</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
          <span className="text-[11px] text-slate-500 uppercase tracking-wider font-mono font-medium block">Total Evacuees</span>
          <span className="text-2xl font-mono font-bold text-slate-900 mt-1 block">
            {totalPop.toLocaleString()}
          </span>
          <span className="text-[11px] text-slate-500 block mt-1 font-medium">Across all hazard zones</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
          <span className="text-[11px] text-slate-500 uppercase tracking-wider font-mono font-medium block">Max Flow Rate</span>
          <span className="text-2xl font-mono font-bold text-blue-700 mt-1 block">
            {maxHourlyFlow.toLocaleString()}
            <span className="text-xs text-slate-500 font-normal ml-1">p/h</span>
          </span>
          <span className="text-[11px] text-slate-500 block mt-1 font-medium">Dinic peak throughput</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
          <span className="text-[11px] text-slate-500 uppercase tracking-wider font-mono font-medium block">Clearance Time</span>
          <span className="text-2xl font-mono font-bold text-emerald-700 mt-1 block">
            {clearanceHours > 0 ? `${clearanceHours.toFixed(1)} hrs` : "Instant"}
          </span>
          <span className="text-[11px] text-slate-500 block mt-1 font-medium">Under optimal dispatch</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-xs">
          <span className="text-[11px] text-slate-500 uppercase tracking-wider font-mono font-medium block">Unmet Evac Demand</span>
          <span
            className={`text-2xl font-mono font-bold mt-1 block ${
              dinicResult?.unmet_demand && dinicResult.unmet_demand > 0
                ? "text-red-600"
                : "text-slate-800"
            }`}
          >
            {dinicResult?.unmet_demand ? dinicResult.unmet_demand.toLocaleString() : "0"}
          </span>
          <span className="text-[11px] text-slate-500 block mt-1 font-medium">Beyond network throughput</span>
        </div>
      </div>

      {/* Interactive Step-by-Step Playback Controller */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-100">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                Augmenting Path Step {frames.length > 0 ? currentFrameIndex + 1 : 0} of {frames.length}
              </span>
              {activeFrame && (
                <span className="text-xs font-mono text-slate-500 font-medium">
                  BFS Level Phase: {activeFrame.phase_index}
                </span>
              )}
            </div>
            <h3 className="text-sm font-bold text-slate-900 mt-1.5">
              {activeFrame ? activeFrame.explanation : "No simulation trace loaded"}
            </h3>
          </div>

          {/* Transport Controls */}
          <div className="flex items-center gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-200 shadow-xs">
            <button
              onClick={handleReset}
              title="Reset to Step 1"
              className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={handleStepPrev}
              disabled={currentFrameIndex <= 0}
              title="Previous Step"
              className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 disabled:opacity-30 transition-colors"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              title={isPlaying ? "Pause" : "Play"}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span className="text-xs">{isPlaying ? "Pause" : "Play"}</span>
            </button>
            <button
              onClick={handleStepNext}
              disabled={currentFrameIndex >= frames.length - 1}
              title="Next Step"
              className="p-1.5 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-200/70 disabled:opacity-30 transition-colors"
            >
              <SkipForward className="w-4 h-4" />
            </button>

            <div className="h-4 w-px bg-slate-200 mx-1"></div>

            <select
              value={playbackSpeed}
              onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
              className="bg-transparent border-none text-slate-700 font-semibold text-xs focus:outline-none cursor-pointer pr-1"
            >
              <option value={1500}>0.7x (Slow)</option>
              <option value={1000}>1.0x (Normal)</option>
              <option value={500}>2.0x (Fast)</option>
            </select>
          </div>
        </div>

        {/* Progress Scrubber */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-slate-600">
            <span>Augmented Flow: <strong className="text-blue-700 font-mono font-bold">{currentFlow.toLocaleString()} p/h</strong></span>
            <span>Target Max Flow: <strong className="text-slate-900 font-mono font-bold">{maxCumulativeFlow.toLocaleString()} p/h</strong> ({flowProgressPct.toFixed(0)}%)</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden border border-slate-200">
            <div
              className="bg-gradient-to-r from-blue-600 to-emerald-500 h-full transition-all duration-300"
              style={{ width: `${flowProgressPct}%` }}
            ></div>
          </div>
        </div>

        {/* Active Frame Details */}
        {activeFrame && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
              <span className="text-[11px] font-semibold text-slate-500 block">Active Path Nodes</span>
              <div className="text-xs font-mono font-bold text-blue-700 mt-1 flex flex-wrap items-center gap-1">
                {activeFrame.active_path_nodes.map((node, i) => (
                  <React.Fragment key={i}>
                    <span className="px-2 py-0.5 bg-white rounded border border-slate-200 shadow-xs">{node}</span>
                    {i < activeFrame.active_path_nodes.length - 1 && <span className="text-slate-400">&rarr;</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
              <span className="text-[11px] font-semibold text-slate-500 block">Flow Pushed In Step</span>
              <span className="text-sm font-mono font-bold text-amber-700 mt-1 block">
                +{activeFrame.flow_sent_this_step.toLocaleString()} evacuees/hr
              </span>
              <span className="text-[11px] text-slate-500 block mt-0.5 font-medium">
                Active roads: {activeFrame.active_road_ids.join(", ") || "Direct"}
              </span>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200">
              <span className="text-[11px] font-semibold text-slate-500 block">
                <TermTooltip termKey="reverse-edge">Reverse Residual Reroutes</TermTooltip>
              </span>
              <span className="text-xs text-slate-700 mt-1 block leading-relaxed font-mono">
                {activeFrame.rerouted_road_ids.length > 0
                  ? `Rerouted corridors: ${activeFrame.rerouted_road_ids.join(", ")}`
                  : "Standard forward augmentation without reverse undo."}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Hourly Evacuation Clearance Curves */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recharts Clearance Area Chart (2/3) */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl p-6 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                Hourly Evacuation Wave Clearance Timeline
              </h3>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Progression of cumulative evacuees safe vs stranded over dispatch hours.
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={scheduleChartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="evacGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#059669" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#059669" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="remainGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#dc2626" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#dc2626" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="hour" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    borderColor: "#cbd5e1",
                    fontSize: "12px",
                    color: "#0f172a",
                    borderRadius: "0.75rem",
                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }} />
                <Area
                  type="monotone"
                  dataKey="cumEvacuated"
                  name="Cumulative Evacuated"
                  stroke="#059669"
                  fillOpacity={1}
                  fill="url(#evacGrad)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="stillRemaining"
                  name="Remaining In Hazard"
                  stroke="#dc2626"
                  fillOpacity={1}
                  fill="url(#remainGrad)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Hourly Dispatch Schedule Table (1/3) */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="pb-3 border-b border-slate-100 mb-3">
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Clearance Schedule</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">Hour-by-hour operational evacuation dispatch.</p>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl max-h-56">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-mono font-bold border-b border-slate-200">
                  <tr>
                    <th className="py-2.5 px-3">Hour</th>
                    <th className="py-2.5 px-3">Cleared</th>
                    <th className="py-2.5 px-3">Remaining</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {waveSchedule.map((entry) => (
                    <tr key={entry.hour} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-2 px-3 text-slate-700 font-semibold">T+{entry.hour}h</td>
                      <td className="py-2 px-3 text-emerald-700 font-bold">+{entry.evacuated_this_hour}</td>
                      <td className="py-2 px-3 text-red-600 font-bold">{entry.remaining_population}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-50/60 rounded-xl border border-blue-100 text-[11px] text-slate-700 flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
            <span className="leading-relaxed">
              Network reaches steady-state throughput at hour 1. Additional relief teams should be deployed along saturated arterial roads.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
