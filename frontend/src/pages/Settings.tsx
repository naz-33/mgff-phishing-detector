import React, { useEffect, useState } from 'react';
import {
  Mail,
  RefreshCw,
  Cpu,
  Layers,
  Lock,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { api } from '../services/api';
import type { ModelInfo, ScannerStatus } from '../types';

export const Settings: React.FC = () => {
  const [scannerStatus, setScannerStatus] = useState<ScannerStatus | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [scanner, model] = await Promise.all([
        api.getScannerStatus(),
        api.getModelInfo(),
      ]);
      setScannerStatus(scanner);
      setModelInfo(model);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load status configurations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <p className="text-xs text-slate-500 font-medium">Querying scanner and model status...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Scanner &amp; Model Architecture Settings
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            System configuration, OAuth 2.0 authorization, and machine learning pipeline telemetry.
          </p>
        </div>

        <button
          onClick={loadData}
          className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-colors shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid: Gmail Scanner Status & Machine Learning Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section 1: Gmail Scanner & Sync State */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Mail className="w-4 h-4 text-blue-600" />
              Gmail Monitoring Integration
            </h2>
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              {scannerStatus?.sync_status || 'ACTIVE'}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Connected Mailbox</span>
                <p className="font-bold text-slate-800 text-sm mt-0.5">
                  {scannerStatus?.mailbox || 'nazlahnanding13@gmail.com'}
                </p>
              </div>
              <Mail className="w-5 h-5 text-blue-500" />
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">OAuth 2.0 Authorization</span>
                <p className="text-slate-700 mt-0.5 flex items-center gap-1 font-medium">
                  {scannerStatus?.oauth_authorized ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Valid Authorized Token (gmail.readonly scope)</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                      <span>Authorization Needed</span>
                    </>
                  )}
                </p>
              </div>
              <Lock className="w-5 h-5 text-slate-400" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Polling Interval</span>
                <p className="text-slate-800 font-bold mt-0.5">{scannerStatus?.polling_interval_seconds || 60} seconds</p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Last Sync Check</span>
                <p className="text-slate-800 font-bold mt-0.5 truncate">
                  {scannerStatus?.last_sync_at ? new Date(scannerStatus.last_sync_at).toLocaleTimeString() : 'Recent'}
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Last Internal Date Checkpoint</span>
              <p className="text-slate-700 font-mono mt-0.5">
                {scannerStatus?.last_internal_date ? `${scannerStatus.last_internal_date} (Monotonic epoch ms)` : 'Synchronized'}
              </p>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-100 text-[11px] text-blue-900 leading-relaxed">
            <strong>Read-Only Monitoring State:</strong> The background scanner runs as a decoupled standalone daemon service (<code>python monitor.py</code>). Scanner lifecycle is managed via process supervision to protect system stability.
          </div>
        </div>

        {/* Section 2: Machine Learning Prediction Engine Specs */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-600" />
              Machine Learning Engine Status
            </h2>
            <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold">
              {modelInfo?.model_version || 'v1.0'}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Ensemble Blending Weights</span>
              <div className="grid grid-cols-2 gap-2 mt-1.5 font-medium">
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-500">Logistic Regression:</span>
                  <span className="font-bold text-blue-600 ml-1.5">
                    {((modelInfo?.ensemble_weights.logistic_regression || 0.5) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="p-2 bg-white rounded-lg border border-slate-200">
                  <span className="text-slate-500">LightGBM:</span>
                  <span className="font-bold text-emerald-600 ml-1.5">
                    {((modelInfo?.ensemble_weights.lightgbm || 0.5) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Decision Threshold</span>
                <p className="font-mono font-bold text-slate-800 text-sm mt-0.5">
                  τ = {modelInfo?.threshold.toFixed(2) || '0.50'}
                </p>
              </div>
              <div className="text-right text-[11px] text-slate-400">
                P ≥ 0.50 → Phishing<br />P &lt; 0.50 → Legitimate
              </div>
            </div>

            {/* Model Artifacts Loaded */}
            <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">Saved Model Artifacts</span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                {modelInfo?.models_loaded &&
                  Object.entries(modelInfo.models_loaded).map(([name, loaded]) => (
                    <div key={name} className="flex items-center space-x-1.5 text-slate-700">
                      {loaded ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />
                      )}
                      <span className="capitalize">{name.replace('_', ' ')}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-600">
            <strong>System:</strong> {modelInfo?.system_name || 'ZanderEtAlFishing'} • Multi-Granularity Feature Fusion
          </div>
        </div>
      </div>

      {/* Feature Engineering Technical Specifications */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-600" />
          Multi-Granularity Feature Fusion Pipeline Specification
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {modelInfo?.architecture.feature_breakdown.map((item, idx) => (
            <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-slate-800">{item.stream}</span>
                <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-mono text-[10px] font-bold">
                  {item.dimension.toLocaleString()} dims
                </span>
              </div>
              <p className="text-slate-500 text-[11px] mt-1 leading-relaxed">{item.details}</p>
              {item.ngrams !== 'N/A' && (
                <span className="inline-block mt-2 text-[10px] font-semibold text-slate-400 bg-slate-200/60 px-2 py-0.5 rounded">
                  {item.ngrams}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
