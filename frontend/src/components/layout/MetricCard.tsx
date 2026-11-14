import React from "react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  accentColor?: "blue" | "emerald" | "amber" | "red" | "slate";
  badge?: string;
  isPending?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  accentColor = "blue",
  badge,
  isPending = false,
}) => {
  const colorMap = {
    blue: {
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
      iconColor: "text-blue-400",
      accentBorder: "hover:border-blue-500/40",
    },
    emerald: {
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      iconColor: "text-emerald-400",
      accentBorder: "hover:border-emerald-500/40",
    },
    amber: {
      bg: "bg-amber-500/10",
      border: "border-amber-500/20",
      iconColor: "text-amber-400",
      accentBorder: "hover:border-amber-500/40",
    },
    red: {
      bg: "bg-red-500/10",
      border: "border-red-500/20",
      iconColor: "text-red-400",
      accentBorder: "hover:border-red-500/40",
    },
    slate: {
      bg: "bg-slate-800/40",
      border: "border-slate-700/40",
      iconColor: "text-slate-400",
      accentBorder: "hover:border-slate-600/60",
    },
  };

  const currentTheme = colorMap[accentColor];

  return (
    <div
      className={`bg-slate-900 border ${currentTheme.border} ${currentTheme.accentBorder} rounded-xl p-4 transition-all duration-200 shadow-sm relative overflow-hidden`}
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-[11px] font-semibold tracking-wider uppercase text-slate-400">
            {title}
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            {isPending ? (
              <span className="text-xl font-bold text-amber-400/90 italic tracking-tight">
                Pending Run
              </span>
            ) : (
              <span className="text-2xl font-bold tracking-tight text-white font-mono">
                {typeof value === "number" ? value.toLocaleString() : value}
              </span>
            )}
            {badge && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {badge}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-400 mt-1 truncate">{subtitle}</p>
          )}
        </div>

        <div
          className={`w-9 h-9 rounded-lg ${currentTheme.bg} border ${currentTheme.border} flex items-center justify-center ${currentTheme.iconColor} shrink-0`}
        >
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
};
