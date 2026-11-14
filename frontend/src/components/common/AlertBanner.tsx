import React from "react";
import { AlertCircle, CheckCircle2, Info, Loader2, X } from "lucide-react";
import { useApp } from "../../context/AppContext";

export const AlertBanner: React.FC = () => {
  const { error, notification, isLoading, loadingMessage, clearError, clearNotification } = useApp();

  return (
    <>
      {/* Global Progress Modal / Loading Overlay */}
      {isLoading && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-2xl flex items-center gap-4 max-w-md w-full">
            <Loader2 className="w-6 h-6 text-blue-600 animate-spin shrink-0" />
            <div>
              <div className="text-sm font-bold text-slate-900">
                ResQ Optimization Engine
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {loadingMessage || "Computing network evacuation flows..."}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Global Error Notice */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-2.5 text-xs text-red-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span className="font-bold">Incident Alert:</span>
            <span>{error}</span>
          </div>
          <button
            onClick={clearError}
            className="p-1 hover:bg-red-100 rounded transition-colors text-red-600"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Global Notification Toast / Banner */}
      {notification && !error && (
        <div
          className={`border-b px-6 py-2.5 text-xs flex items-center justify-between transition-colors shadow-xs ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800 font-medium"
              : notification.type === "warning"
              ? "bg-amber-50 border-amber-200 text-amber-900 font-medium"
              : "bg-blue-50 border-blue-200 text-blue-800 font-medium"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : notification.type === "warning" ? (
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-blue-600 shrink-0" />
            )}
            <span>{notification.message}</span>
          </div>
          <button
            onClick={clearNotification}
            className="p-1 hover:bg-slate-200/60 rounded transition-colors text-slate-400 hover:text-slate-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </>
  );
};
