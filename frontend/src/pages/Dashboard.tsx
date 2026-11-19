import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Mail,
  Clock,
  Zap,
  ArrowRight,
  AlertTriangle,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { api } from '../services/api';
import type { DashboardSummary, EmailScanItem } from '../types';

// ─── Three-tier risk helper (shared pattern) ──────────────────────────────────
type RiskTier = 'phishing' | 'suspicious' | 'legitimate';

function getRiskTier(email: EmailScanItem): RiskTier {
  if (email.risk_tier === 'High-Confidence Phishing') return 'phishing';
  if (email.risk_tier === 'Suspicious') return 'suspicious';
  if (email.risk_tier === 'Legitimate') return 'legitimate';
  const p = email.phishing_probability;
  if (p >= 0.70) return 'phishing';
  if (p >= 0.50) return 'suspicious';
  return 'legitimate';
}

export const Dashboard: React.FC = () => {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const loadData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    try {
      const data = await api.getDashboardSummary();
      setSummary(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh summary every 30 seconds
    const interval = setInterval(() => loadData(), 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-3">
        <RefreshCw className="w-8 h-8 text-blue-600 animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading monitoring data...</p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800">
        <div className="flex items-center space-x-3">
          <AlertTriangle className="w-6 h-6 text-rose-600" />
          <h2 className="text-base font-bold">Error loading dashboard</h2>
        </div>
        <p className="mt-2 text-sm text-rose-600">{error || 'Unable to retrieve summary metrics.'}</p>
        <button
          onClick={() => loadData(true)}
          className="mt-4 px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-semibold hover:bg-rose-700"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const pieData = [
    { name: 'High-Confidence Phishing', value: summary.total_phishing - (summary.total_suspicious ?? 0), color: '#ef4444' },
    { name: 'Suspicious', value: summary.total_suspicious ?? 0, color: '#f59e0b' },
    { name: 'Legitimate', value: summary.total_legitimate, color: '#10b981' },
  ].filter(d => d.value > 0);

  return (
    <div className="space-y-6">
      {/* Top Banner / Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-blue-600 uppercase tracking-wider mb-1">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping"></span>
            <span>Live Security Telemetry</span>
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Security Monitoring Center
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Real-time phishing email classification powered by multi-granularity feature fusion with hybrid Logistic Regression and LightGBM.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition-all"
            title="Refresh current data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <Link
            to="/emails"
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-md shadow-blue-500/20 transition-all"
          >
            <span>Inspect All Emails</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* System Status Indicators Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Scanned */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Scanned</p>
            <h3 className="text-3xl font-black text-slate-900 mt-2">{summary.total_scanned.toLocaleString()}</h3>
            <p className="text-[11px] text-slate-400 mt-1">Processed from Gmail inbox</p>
          </div>
          <div className="p-3 bg-blue-50 rounded-xl text-blue-600">
            <Mail className="w-5 h-5" />
          </div>
        </div>

        {/* High-Confidence Phishing Detections */}
        <div className="bg-white p-5 rounded-2xl border border-rose-100 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-rose-600 uppercase tracking-wider">High-Conf. Phishing</p>
            <h3 className="text-3xl font-black text-rose-600 mt-2">
              {(summary.total_phishing - (summary.total_suspicious ?? 0)).toLocaleString()}
            </h3>
            <p className="text-[11px] text-rose-500 mt-1">Probability ≥ 70%</p>
          </div>
          <div className="p-3 bg-rose-50 rounded-xl text-rose-600">
            <ShieldAlert className="w-5 h-5" />
          </div>
        </div>

        {/* Suspicious — Needs Review */}
        <div className="bg-white p-5 rounded-2xl border border-amber-100 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-amber-600 uppercase tracking-wider">Suspicious</p>
            <h3 className="text-3xl font-black text-amber-600 mt-2">{(summary.total_suspicious ?? 0).toLocaleString()}</h3>
            <p className="text-[11px] text-amber-500 mt-1">Borderline 50–70% — review</p>
          </div>
          <div className="p-3 bg-amber-50 rounded-xl text-amber-600">
            <ShieldQuestion className="w-5 h-5" />
          </div>
        </div>

        {/* Average Inference Latency */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-start justify-between">
          <div>
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Avg Inference Latency</p>
            <h3 className="text-3xl font-black text-slate-900 mt-2">{summary.average_latency_ms.toFixed(1)} <span className="text-sm font-semibold text-slate-500">ms</span></h3>
            <p className="text-[11px] text-slate-400 mt-1">Multi-granularity hybrid inference</p>
          </div>
          <div className="p-3 bg-amber-50 rounded-xl text-amber-600">
            <Zap className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Gateway Authentication Trust Signals Legend */}
      <div className="bg-white px-5 py-3 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-2 text-xs font-medium text-slate-600">
          <span className="font-bold text-slate-700">Gateway Authentication Checks:</span>
          <span>Gmail header verification (SPF, DKIM, DMARC) acts as an independent trust layer alongside ML predictions.</span>
        </div>
        <div className="flex items-center space-x-4 text-xs font-medium">
          <div className="flex items-center space-x-1.5 text-emerald-700 bg-emerald-50 px-2 py-1 rounded-lg border border-emerald-100">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>SPF Verified</span>
          </div>
          <div className="flex items-center space-x-1.5 text-blue-700 bg-blue-50 px-2 py-1 rounded-lg border border-blue-100">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>DKIM Signed</span>
          </div>
          <div className="flex items-center space-x-1.5 text-indigo-700 bg-indigo-50 px-2 py-1 rounded-lg border border-indigo-100">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>DMARC Passed</span>
          </div>
        </div>
      </div>

      {/* Overview Analytics Bar: Distribution & Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Classification Breakdown Chart */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm lg:col-span-1 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 tracking-tight">Classification Ratio</h3>
            <p className="text-xs text-slate-500 mt-0.5">Distribution across all scanned messages</p>
          </div>

          <div className="h-48 my-2 flex items-center justify-center">
            {summary.total_scanned > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: any) => [`${val} emails`, 'Count']}
                    contentStyle={{ borderRadius: '12px', fontSize: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-slate-400">No scanned email data yet</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100">
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-rose-500"></span>
              <div>
                <p className="text-[11px] text-slate-500">High-Conf. Phishing</p>
                <p className="text-xs font-bold text-slate-800">
                  {Math.max(0, summary.total_phishing - (summary.total_suspicious ?? 0))} emails
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-amber-400"></span>
              <div>
                <p className="text-[11px] text-slate-500">Suspicious</p>
                <p className="text-xs font-bold text-slate-800">{summary.total_suspicious ?? 0} emails</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 col-span-2">
              <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
              <div>
                <p className="text-[11px] text-slate-500">Legitimate</p>
                <p className="text-xs font-bold text-slate-800">{summary.total_legitimate} ({(100 - summary.phishing_ratio_percent).toFixed(1)}%)</p>
              </div>
            </div>
          </div>
        </div>

        {/* Recent High-Confidence Phishing Warnings Banner */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-lg bg-rose-100 text-rose-700">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-slate-900 tracking-tight">Recent High-Confidence Phishing</h3>
            </div>
            <span className="text-xs font-medium text-rose-600 bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200">
              ≥ 70% Threat Score
            </span>
          </div>

          {summary.recent_phishing_warnings.length > 0 ? (
            <div className="space-y-3">
              {summary.recent_phishing_warnings.slice(0, 4).map((warning) => {
                const tier = getRiskTier(warning);
                return (
                  <div
                    key={warning.id}
                    className={`p-3.5 rounded-xl border hover:opacity-90 transition-opacity flex items-center justify-between ${tier === 'suspicious'
                        ? 'bg-amber-50/60 border-amber-200/70'
                        : 'bg-rose-50/60 border-rose-200/70'
                      }`}
                  >
                    <div className="min-w-0 flex-1 pr-4">
                      <p className="text-xs font-bold text-slate-900 truncate">
                        {warning.subject || '(No Subject)'}
                      </p>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5">
                        From: <span className="font-medium text-slate-700">{warning.sender}</span>
                      </p>
                    </div>

                    <div className="flex items-center space-x-3 shrink-0">
                      <div className="text-right">
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold text-white ${tier === 'suspicious' ? 'bg-amber-500' : 'bg-rose-600'
                          }`}>
                          {(warning.phishing_probability * 100).toFixed(1)}% {tier === 'suspicious' ? 'Suspicious' : 'Threat'}
                        </span>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {new Date(warning.scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>

                      <Link
                        to={`/emails/${warning.id}`}
                        className="p-1.5 rounded-lg bg-white text-slate-600 hover:text-blue-600 border border-slate-200 shadow-sm"
                        title="View inspection details"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center p-8 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center">
              <ShieldCheck className="w-8 h-8 text-emerald-500 mb-2" />
              <p className="text-xs font-semibold text-slate-700">No Phishing Threats Detected</p>
              <p className="text-[11px] text-slate-400 mt-0.5">All recently scanned emails passed threshold validation.</p>
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              Latest Scan: {summary.latest_scan_at ? new Date(summary.latest_scan_at).toLocaleString() : 'N/A'}
            </span>
            <span className="font-medium text-blue-600">Thresholds: 0.50 / 0.70</span>
          </div>
        </div>
      </div>

      {/* Recent Monitored Emails Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight">Recent Monitored Emails</h3>
            <p className="text-xs text-slate-500 mt-0.5">Latest messages ingested and scanned from Gmail</p>
          </div>
          <Link
            to="/emails"
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center space-x-1"
          >
            <span>View All Records</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {summary.recent_scans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-6">Classification</th>
                  <th className="py-3 px-6">Subject</th>
                  <th className="py-3 px-6">Sender</th>
                  <th className="py-3 px-6 text-center">Phishing Prob</th>
                  <th className="py-3 px-6">Scanned At</th>
                  <th className="py-3 px-6 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {summary.recent_scans.map((email) => {
                  const tier = getRiskTier(email);
                  const tierConfig = {
                    phishing: { label: 'High-Conf. Phishing', cls: 'bg-rose-100 text-rose-700 border border-rose-300', Icon: ShieldAlert, iconCls: 'text-rose-600' },
                    suspicious: { label: 'Suspicious', cls: 'bg-amber-100 text-amber-700 border border-amber-300', Icon: ShieldQuestion, iconCls: 'text-amber-600' },
                    legitimate: { label: 'Legitimate', cls: 'bg-emerald-100 text-emerald-700 border border-emerald-300', Icon: ShieldCheck, iconCls: 'text-emerald-600' },
                  }[tier];
                  return (
                    <tr key={email.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-6 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold ${tierConfig.cls}`}>
                          <tierConfig.Icon className={`w-3 h-3 mr-1 ${tierConfig.iconCls}`} />
                          {tierConfig.label}
                        </span>
                      </td>

                      <td className="py-3 px-6 max-w-xs truncate font-medium text-slate-900">
                        {email.subject || '(No Subject)'}
                      </td>

                      <td className="py-3 px-6 max-w-xs truncate text-slate-500">
                        {email.sender}
                      </td>

                      <td className="py-3 px-6 text-center whitespace-nowrap">
                        <span className="font-mono font-semibold text-slate-800">
                          {(email.phishing_probability * 100).toFixed(2)}%
                        </span>
                      </td>

                      <td className="py-3 px-6 whitespace-nowrap text-slate-500 text-[11px]">
                        {new Date(email.scanned_at).toLocaleString()}
                      </td>

                      <td className="py-3 px-6 text-right whitespace-nowrap">
                        <Link
                          to={`/emails/${email.id}`}
                          className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-600 font-medium transition-colors"
                        >
                          <span>Details</span>
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center text-slate-400 text-xs">
            <Mail className="w-8 h-8 mx-auto mb-2 text-slate-300" />
            No monitored emails found in the database.
          </div>
        )}
      </div>
    </div>
  );
};
