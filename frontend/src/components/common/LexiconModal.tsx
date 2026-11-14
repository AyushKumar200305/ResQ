import React, { useState } from "react";
import { BookOpen, Check, Search, Sparkles, X } from "lucide-react";
import { DAA_GLOSSARY } from "./TermTooltip";

interface LexiconModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LexiconModal: React.FC<LexiconModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [search, setSearch] = useState("");

  if (!isOpen) return null;

  const entries = Object.entries(DAA_GLOSSARY).filter(([key, item]) => {
    const q = search.toLowerCase();
    return (
      item.term.toLowerCase().includes(q) ||
      item.simple.toLowerCase().includes(q) ||
      (item.technical && item.technical.toLowerCase().includes(q))
    );
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-600 shadow-xs">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                Emergency Evacuation Lexicon &amp; DAA Guide
              </h2>
              <p className="text-xs text-slate-500 font-medium">
                Core concepts explained in simple, clear language.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-200/60 text-slate-400 hover:text-slate-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Input */}
        <div className="p-4 border-b border-slate-100 bg-white">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search concepts (e.g. Maximum Flow, Min-Cut, Bottleneck, Residual)..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 shadow-xs"
            />
          </div>
        </div>

        {/* Glossary List */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1 divide-y divide-slate-100">
          {entries.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">
              No matching definitions found for "{search}".
            </div>
          ) : (
            entries.map(([key, item]) => (
              <div key={key} className="pt-4 first:pt-0">
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="text-sm font-bold text-blue-700">
                    {item.term}
                  </span>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                    DAA Core
                  </span>
                </div>
                <p className="text-xs text-slate-700 leading-relaxed">
                  {item.simple}
                </p>
                {item.technical && (
                  <div className="mt-2 text-[11px] text-slate-600 font-mono bg-slate-50 p-3 rounded-xl border border-slate-200 leading-relaxed">
                    <span className="text-blue-700 font-bold font-sans">
                      Mathematical Context:{" "}
                    </span>
                    {item.technical}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs text-slate-500">
          <span className="font-medium">ResQ Algorithmic Reference Manual</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold shadow-xs transition-colors"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
};
